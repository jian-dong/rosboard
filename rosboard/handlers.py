import json
import socket
import time
import tornado
import tornado.web
import tornado.websocket
import traceback
import uuid

from . import __version__

class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # Disable cache
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

class ROSBoardSocketHandler(tornado.websocket.WebSocketHandler):
    sockets = set()
    def initialize(self, node):
        # store the instance of the ROS node that created this WebSocketHandler so we can access it later
        self.node = node

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    def open(self):
        self.id = uuid.uuid4()    # unique socket id
        self.latency = 0          # latency measurement
        self.clock_diff = 0       # clock difference measurement
        self.last_ping_time = 0
        self.last_pong_time = 0

        self.update_intervals_by_topic = {}  # this socket's throttle rate on each topic
        self.last_data_times_by_topic = {}   # last time this socket received data on each topic

        ROSBoardSocketHandler.sockets.add(self)

        self.write_message(json.dumps([ROSBoardSocketHandler.MSG_SYSTEM, {
            "hostname": socket.gethostname(),
            "version": __version__,
        }]))

    def on_close(self):
        ROSBoardSocketHandler.sockets.remove(self)

        # when socket closes, remove ourselves from all subscriptions
        for topic_name in self.node.remote_subs:
            if self.id in self.node.remote_subs[topic_name]:
                self.node.remote_subs[topic_name].remove(self.id)

    @classmethod
    def send_pings(cls):
        """
        Send pings to all sockets. When pongs are received they will be used for measuring
        latency and clock differences.
        """

        for socket in cls.sockets:
            try:
                socket.last_ping_time = time.time() * 1000
                socket.write_message(json.dumps([ROSBoardSocketHandler.MSG_PING]))
            except Exception as e:
                print("Error sending message: %s", str(e))

    @classmethod
    def broadcast(cls, message):
        """
        Broadcasts a dict-ified ROS message (message) to all sockets that care about that topic.
        The dict message should contain metadata about what topic it was
        being sent on: message["_topic_name"], message["_topic_type"].
        """

        for socket in cls.sockets:
            try:
                if message[0] == ROSBoardSocketHandler.MSG_TOPICS:
                    socket.write_message(json.dumps(message))
                elif message[0] == ROSBoardSocketHandler.MSG_MSG:
                    topic_name = message[1]["_topic_name"]
                    if topic_name not in socket.node.remote_subs:
                        continue
                    if socket.id not in socket.node.remote_subs[topic_name]:
                        continue

                    t = time.time()
                    if t - socket.last_data_times_by_topic.get(topic_name, 0.0) < \
                            socket.update_intervals_by_topic.get(topic_name) - 2e-4:
                        continue

                    ros_msg_dict = message[1]

                    socket.write_message(json.dumps([ROSBoardSocketHandler.MSG_MSG, ros_msg_dict]))
                    socket.last_data_times_by_topic[topic_name] = t
            except Exception as e:
                print("Error sending message: %s" % str(e))
                traceback.print_exc()

    def on_message(self, message):
        """
        Message received from the client.
        """

        # JSON decode it, give up if it isn't valid JSON
        try:
            argv = json.loads(message)
        except (ValueError, TypeError):
            print("error: bad: %s" % message)
            return

        # make sure the received argv is a list and the first element is a string and indicates the type of command
        if type(argv) is not list or len(argv) < 1 or type(argv[0]) is not str:
            print("error: bad: %s" % message)
            return

        # if it was a ping command, respond with a pong including our system time
        if argv[0] == ROSBoardSocketHandler.MSG_PING:
            if len(argv) != 1:
                print("error: ping: bad: %s" % message)
                return
            self.write_message(json.dumps([ROSBoardSocketHandler.MSG_PONG, time.time()]))

        # if we got a pong for our own ping, compute latency and clock difference
        elif argv[0] == ROSBoardSocketHandler.MSG_PONG:
            if len(argv) != 2 or type(argv[1]) is not dict:
                print("error: pong: bad: %s" % message)
                return

            remote_clock_time = argv[1].get(ROSBoardSocketHandler.PONG_TIME, 0)
            self.last_pong_time = time.time() * 1000
            self.latency = (self.last_pong_time - self.last_ping_time) / 2
            self.clock_diff = 0.95 * self.clock_diff + 0.05 * ((self.last_pong_time + self.last_ping_time) / 2 - remote_clock_time)

        # client wants to subscribe to topic
        elif argv[0] == ROSBoardSocketHandler.MSG_SUB:
            if len(argv) != 2 or type(argv[1]) is not dict:
                print("error: sub: bad: %s" % message)
                return

            topic_name = argv[1].get("topicName")
            max_update_rate = float(argv[1].get("maxUpdateRate", 24.0))

            self.update_intervals_by_topic[topic_name] = 1.0 / max_update_rate
            self.node.update_intervals_by_topic[topic_name] = min(
                self.node.update_intervals_by_topic.get(topic_name, 1.),
                self.update_intervals_by_topic[topic_name]
            )

            if topic_name is None:
                print("error: no topic specified")
                return

            if topic_name not in self.node.remote_subs:
                self.node.remote_subs[topic_name] = set()

            self.node.remote_subs[topic_name].add(self.id)
            self.node.sync_subs()

        # client wants to unsubscribe from topic
        elif argv[0] == ROSBoardSocketHandler.MSG_UNSUB:
            if len(argv) != 2 or type(argv[1]) is not dict:
                print("error: unsub: bad: %s" % message)
                return
            topic_name = argv[1].get("topicName")

            if topic_name not in self.node.remote_subs:
                self.node.remote_subs[topic_name] = set()

            try:
                self.node.remote_subs[topic_name].remove(self.id)
            except KeyError:
                print("KeyError trying to remove sub")

ROSBoardSocketHandler.MSG_PING = "p";
ROSBoardSocketHandler.MSG_PONG = "q";
ROSBoardSocketHandler.MSG_MSG = "m";
ROSBoardSocketHandler.MSG_TOPICS = "t";
ROSBoardSocketHandler.MSG_SUB = "s";
ROSBoardSocketHandler.MSG_SYSTEM = "y";
ROSBoardSocketHandler.MSG_UNSUB = "u";

ROSBoardSocketHandler.PONG_TIME = "t";

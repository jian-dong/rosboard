#!/usr/bin/env python3

"""
Mimics the functionality of cv_bridge but in pure python, without OpenCV dependency.

An additional optional flip_channels argument is provided in the imgmsg_to_cv2() function
for convenience (e.g. if resulting numpy array is going to be fed directly into a neural network
that expects channels in RGB order instead of OpenCV-ish BGR).

Author: dheera@dheera.net
"""

import numpy

BPP = {
  'bgr8': 3,
  'rgb8': 3,
  '16UC1': 2,
  '8UC1': 1,
  'mono16': 2,
  'mono8': 1
}

def imgmsg_to_cv2(data, desired_encoding="passthrough", flip_channels=False):
    """
    Converts a ROS image to an OpenCV image without using the cv_bridge package,
    for compatibility purposes.
    """

    if desired_encoding == "passthrough":
        encoding = data.encoding
    else:
        encoding = desired_encoding

    if (encoding == 'bgr8' and not flip_channels) or (encoding=='rgb8' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint8).reshape((data.height, data.width, 3))
    elif (encoding == 'rgb8' and not flip_channels) or (encoding=='bgr8' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint8).reshape((data.height, data.width, 3))[:, :, ::-1]
    elif (encoding == 'bgra8' and not flip_channels) or (encoding == 'rgba8' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint8).reshape((data.height, data.width, 4))[:,:,0:3]
    elif (encoding == 'rgba8' and not flip_channels) or (encoding == 'bgra8' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint8).reshape((data.height, data.width, 4))[:, :, ::-1][:,:,1:]
    if (encoding == 'bgr16' and not flip_channels) or (encoding=='rgb16' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint16).reshape((data.height, data.width, 3))
    elif (encoding == 'rgb16' and not flip_channels) or (encoding=='bgr16' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint16).reshape((data.height, data.width, 3))[:, :, ::-1]
    elif (encoding == 'bgra16' and not flip_channels) or (encoding == 'rgba16' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint16).reshape((data.height, data.width, 4))[:,:,0:3]
    elif (encoding == 'rgba16' and not flip_channels) or (encoding == 'bgra16' and flip_channels):
        return numpy.frombuffer(data.data, numpy.uint16).reshape((data.height, data.width, 4))[:, :, ::-1][:,:,1:]
    elif encoding == 'mono8' or encoding == '8UC1':
        return numpy.frombuffer(data.data, numpy.uint8).reshape((data.height, data.width))
    elif encoding == 'mono16' or encoding == '16UC1':
        return numpy.frombuffer(data.data, numpy.uint16).reshape((data.height, data.width))
    else:
        print("Unsupported encoding %s" % encoding)
        return None

def cv2_to_imgmsg(cv2img, encoding='bgr8'):
    """
    Converts an OpenCV image to a ROS image without using the cv_bridge package,
    for compatibility purposes.
    """

    from sensor_msgs.msg import Image
    
    msg = Image()
    msg.width = cv2img.shape[1]
    msg.height = cv2img.shape[0]
    msg.encoding = encoding
    msg.step = BPP[encoding]*cv2img.shape[1]
    msg.data = numpy.ascontiguousarray(cv2img).tobytes()

    return msg

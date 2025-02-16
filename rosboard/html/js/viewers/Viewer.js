"use strict";

class Viewer {
  /**
    * Class constructor.
    * @constructor
  **/
  constructor(card) {
    this.card = card;
    this.onClose = () => {};
    let that = this;

    card.buttons = $('<div></div>').addClass('card-buttons').text('').appendTo(card);
    card.title = $('<div></div>').addClass('card-title').text("Waiting for data ...").appendTo(card);
    card.content = $('<div></div>').addClass('card-content').text('').appendTo(card);
    card.closeButton = $('<button></button>')
      .addClass('mdl-button')
      .addClass('mdl-js-button')
      .addClass('mdl-button--icon')
      .append($('<i></i>').addClass('material-icons').text('close'))
      .appendTo(card.buttons);
    card.closeButton.click(() => { that.onClose.call(that); });

    this.onCreate();

    /// show a spinner; get rid of it after first data is received
    this.spinContainer = $('<div></div>')
      .css({
        position:"absolute",
        display: "flex",
        top: "0",
        left:"0",
        width: "100%",
        "align-items": "center",
        height: "100%",
      })
      .appendTo(this.card);
    $('<div></div>').addClass('loader').appendTo(this.spinContainer);

    this.lastDataTime = 0.0;
  }

  /**
    * Gets called when Viewer is first initialized.
    * @override
  **/
  onCreate() {
    // for MDL elements to get instantiated
    if(!(typeof(componentHandler) === 'undefined')){
      componentHandler.upgradeAllRegistered();
    }
  }

  /**
    * Gets called when Viewer is about to be destroyed.
    * @override
  **/
  onDestroy() { }

  /**
    * Gets called when the window is resized.
    * @override
  **/
  onResize() { }

  /**
    * Adds a topic to the viewer.
    * @override
  **/
  onData(data) { }

  update(data) {  
    let time = Date.now();
    if( (time - this.lastDataTime)/1000.0 < 1/this.constructor.maxUpdateRate - 5e-4) {
      return;
    }

    this.lastDataTime = time;

    // get rid of the spinner
    if(this.spinContainer) {
      this.spinContainer.remove();
      this.spinContainer = null;
    }

    // actually update the data
    this.onData(data);
  }
}

// can be overridden by child class
// list of supported message types by viewer, or "*" for all types
// todo: support regexes?
Viewer.supportedTypes = [];

// can be overridden by child class
// max update rate that this viewer can handle
// for some viewers that do extensive DOM manipulations, this should be set conservatively
Viewer.maxUpdateRate = 50.0;

// not to be overwritten by child class!
// stores registered viewers in sequence of loading
Viewer._viewers = [];

// not to be overwritten by child class!
Viewer.registerViewer = (viewer) => {
  // registers a viewer. the viewer child class calls this at the end of the file to register itself
  Viewer._viewers.push(viewer);
};

// not to be overwritten by child class!
Viewer.getViewerForType = (type) => {
  // gets the viewer class for a given message type (e.g. "std_msgs/msg/String")

  // if type is "package/MessageType", converted it to "package/msgs/MessageType"
  let tokens = type.split("/");
  if(tokens.length == 2) {
    type = [tokens[0], "msg", tokens[1]].join("/");
  }

  // go down the list of registered viewers and return the first match
  for(let i in Viewer._viewers) {
    if(Viewer._viewers[i].supportedTypes.includes(type)) {
      return Viewer._viewers[i];
    }
    if(Viewer._viewers[i].supportedTypes.includes("*")) {
      return Viewer._viewers[i];
    }
  }
  return null;
}

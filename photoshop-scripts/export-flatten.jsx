#target photoshop

app.displayDialogs = DialogModes.NO;

function readArgs() {
  var args = $.arguments || [];
  var psdPath = args.length > 0 ? args[0] : null;
  var outPath = args.length > 1 ? args[1] : null;
  var hideText = args.length > 2 ? args[2] : null;
  if (!psdPath || !outPath) {
    var scriptFile = new File($.fileName);
    var argsFile = new File(scriptFile.parent.fsName + "/export-flatten.args.txt");
    if (argsFile.exists && argsFile.open("r")) {
      var text = argsFile.read();
      argsFile.close();
      var lines = text.split(/\r?\n/);
      psdPath = psdPath || lines[0];
      outPath = outPath || lines[1];
      hideText = hideText || lines[2];
    }
  }
  if (!psdPath) throw new Error("Missing PSD path argument.");
  if (!outPath) throw new Error("Missing output PNG path argument.");
  return { psdPath: psdPath, outPath: outPath, hideText: String(hideText) === "1" };
}

function hideTextLayers(layerContainer) {
  for (var i = 0; i < layerContainer.layers.length; i++) {
    var layer = layerContainer.layers[i];
    if (layer.typename === "LayerSet") {
      hideTextLayers(layer);
    } else if (layer.typename === "ArtLayer") {
      try {
        if (layer.kind === LayerKind.TEXT) layer.visible = false;
      } catch (e) {
      }
    }
  }
}

function main() {
  var args = readArgs();
  var psdFile = new File(args.psdPath);
  if (!psdFile.exists) throw new Error("PSD file does not exist: " + args.psdPath);

  var doc = app.open(psdFile);
  if (args.hideText) hideTextLayers(doc);
  doc.flatten();

  var outFile = new File(args.outPath);
  var outFolder = outFile.parent;
  if (!outFolder.exists) outFolder.create();

  var options = new ExportOptionsSaveForWeb();
  options.format = SaveDocumentType.PNG;
  options.PNG8 = false;
  options.transparency = false;
  options.interlaced = false;
  options.includeProfile = false;
  doc.exportDocument(outFile, ExportType.SAVEFORWEB, options);
  doc.close(SaveOptions.DONOTSAVECHANGES);
}

main();

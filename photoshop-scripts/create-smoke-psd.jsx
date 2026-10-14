#target photoshop

app.displayDialogs = DialogModes.NO;

function readArgs() {
  var args = $.arguments || [];
  var outPath = args.length > 0 ? args[0] : null;
  if (!outPath) {
    var scriptFile = new File($.fileName);
    var argsFile = new File(scriptFile.parent.fsName + "/create-smoke-psd.args.txt");
    if (argsFile.exists && argsFile.open("r")) {
      outPath = argsFile.read().split(/\r?\n/)[0];
      argsFile.close();
    }
  }
  if (!outPath) throw new Error("Missing output PSD path argument.");
  return outPath;
}

function main() {
  var outPath = readArgs();
  var doc = app.documents.add(720, 1280, 72, "psd-web-converter-smoke", NewDocumentMode.RGB, DocumentFill.WHITE);

  var bg = doc.artLayers.add();
  bg.name = "蓝色背景";
  var bgColor = new SolidColor();
  bgColor.rgb.red = 31;
  bgColor.rgb.green = 94;
  bgColor.rgb.blue = 184;
  app.foregroundColor = bgColor;
  doc.selection.select([[0, 0], [720, 0], [720, 1280], [0, 1280]]);
  doc.selection.fill(bgColor);
  doc.selection.deselect();

  var title = doc.artLayers.add();
  title.kind = LayerKind.TEXT;
  title.name = "会议标题";
  title.textItem.contents = "医学会议 H5";
  title.textItem.size = UnitValue(52, "px");
  title.textItem.position = [UnitValue(80, "px"), UnitValue(150, "px")];
  var textColor = new SolidColor();
  textColor.rgb.red = 255;
  textColor.rgb.green = 255;
  textColor.rgb.blue = 255;
  title.textItem.color = textColor;

  var outFile = new File(outPath);
  var options = new PhotoshopSaveOptions();
  doc.saveAs(outFile, options, true, Extension.LOWERCASE);
  doc.close(SaveOptions.DONOTSAVECHANGES);
}

main();

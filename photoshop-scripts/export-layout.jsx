#target photoshop

app.displayDialogs = DialogModes.NO;

function jsonEscape(value) {
  return String(value)
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\r/g, "\\n")
    .replace(/\n/g, "\\n")
    .replace(/\t/g, "\\t");
}

function toJSON(value) {
  var type = typeof value;
  if (value === null || value === undefined) return "null";
  if (type === "number" || type === "boolean") return String(value);
  if (type === "string") return '"' + jsonEscape(value) + '"';
  if (value instanceof Array) {
    var items = [];
    for (var i = 0; i < value.length; i++) items.push(toJSON(value[i]));
    return "[" + items.join(",") + "]";
  }
  var props = [];
  for (var key in value) {
    if (value.hasOwnProperty(key)) props.push('"' + jsonEscape(key) + '":' + toJSON(value[key]));
  }
  return "{" + props.join(",") + "}";
}

function safeString(value) {
  try {
    if (value === null || value === undefined) return null;
    return String(value);
  } catch (e) {
    return null;
  }
}

function unitToPx(value) {
  try {
    if (value === null || value === undefined) return null;
    if (value.as) return Number(value.as("px"));
    return Number(value);
  } catch (e) {
    return null;
  }
}

function boundsToObject(bounds) {
  var left = unitToPx(bounds[0]);
  var top = unitToPx(bounds[1]);
  var right = unitToPx(bounds[2]);
  var bottom = unitToPx(bounds[3]);
  return {
    left: left,
    top: top,
    right: right,
    bottom: bottom,
    width: right - left,
    height: bottom - top
  };
}

function colorToObject(color) {
  try {
    if (!color || !color.rgb) return null;
    return {
      red: Math.round(Number(color.rgb.red)),
      green: Math.round(Number(color.rgb.green)),
      blue: Math.round(Number(color.rgb.blue))
    };
  } catch (e) {
    return null;
  }
}

function getStringProp(object, prop) {
  try {
    return safeString(object[prop]);
  } catch (e) {
    return null;
  }
}

function getUnitProp(object, prop) {
  try {
    return unitToPx(object[prop]);
  } catch (e) {
    return null;
  }
}

function getTextLayerDescriptor() {
  try {
    var ref = new ActionReference();
    ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
    return executeActionGet(ref);
  } catch (e) {
    return null;
  }
}

function descriptorTextValue(desc, key) {
  try {
    var typeId = stringIDToTypeID(key);
    if (!desc || !desc.hasKey(typeId)) return null;
    return safeString(desc.getString(typeId));
  } catch (e) {
    return null;
  }
}

function descriptorNumberValue(desc, key) {
  try {
    var typeId = stringIDToTypeID(key);
    if (!desc || !desc.hasKey(typeId)) return null;
    var type = desc.getType(typeId);
    if (type === DescValueType.UNITDOUBLE) return Number(desc.getUnitDoubleValue(typeId));
    if (type === DescValueType.DOUBLETYPE) return Number(desc.getDouble(typeId));
    if (type === DescValueType.INTEGERTYPE) return Number(desc.getInteger(typeId));
    return null;
  } catch (e) {
    return null;
  }
}

function descriptorObjectValue(desc, key) {
  try {
    var typeId = stringIDToTypeID(key);
    if (!desc || !desc.hasKey(typeId)) return null;
    return desc.getObjectValue(typeId);
  } catch (e) {
    return null;
  }
}

function descriptorListValue(desc, key) {
  try {
    var typeId = stringIDToTypeID(key);
    if (!desc || !desc.hasKey(typeId)) return null;
    return desc.getList(typeId);
  } catch (e) {
    return null;
  }
}

function textKeyStyle(textDesc) {
  var result = {
    font: null,
    sizePx: null,
    leadingPx: null,
    color: null,
    horizontalScale: null,
    justification: null
  };

  try {
    var styleRange = descriptorListValue(textDesc, "textStyleRange");
    if (!styleRange || styleRange.count < 1) return result;
    var firstRange = styleRange.getObjectValue(0);
    var style = descriptorObjectValue(firstRange, "textStyle");
    if (!style) return result;

    result.font = descriptorTextValue(style, "fontPostScriptName") || descriptorTextValue(style, "fontName");
    result.sizePx = descriptorNumberValue(style, "size");
    result.leadingPx = descriptorNumberValue(style, "leading");
    result.horizontalScale = safeString(descriptorNumberValue(style, "horizontalScale"));

    var colorDesc = descriptorObjectValue(style, "color");
    if (colorDesc) {
      result.color = {
        red: Math.round(descriptorNumberValue(colorDesc, "red") || 0),
        green: Math.round(descriptorNumberValue(colorDesc, "green") || 0),
        blue: Math.round(descriptorNumberValue(colorDesc, "blue") || 0)
      };
    }
  } catch (e) {
  }
  return result;
}

function getTextKeyMetadata(layer) {
  try {
    app.activeDocument.activeLayer = layer;
  } catch (e0) {
    return null;
  }

  var layerDesc = getTextLayerDescriptor();
  if (!layerDesc) return null;

  try {
    var textKeyId = stringIDToTypeID("textKey");
    if (!layerDesc.hasKey(textKeyId)) return null;
    var textDesc = layerDesc.getObjectValue(textKeyId);
    var contents = descriptorTextValue(textDesc, "textKey");
    if (!contents) contents = descriptorTextValue(textDesc, "text");
    if (!contents) return null;
    var style = textKeyStyle(textDesc);

    return {
      contents: contents,
      font: style.font,
      sizePx: style.sizePx,
      leadingPx: style.leadingPx,
      tracking: null,
      horizontalScale: style.horizontalScale,
      verticalScale: null,
      baselineShiftPx: null,
      justification: style.justification,
      kind: "textKey",
      position: null,
      widthPx: null,
      heightPx: null,
      color: style.color,
      source: "textKey",
      warning: "Photoshop textItem 读取失败，已使用 Action Manager textKey 读取文字内容。"
    };
  } catch (e) {
    return null;
  }
}

function textFromLayerName(layer) {
  var name = safeString(layer.name);
  if (!name) return null;
  if (/^(图层|Layer|形状|矩形|组)\s*\d*/.test(name)) return null;
  return {
    contents: name,
    font: null,
    sizePx: null,
    leadingPx: null,
    tracking: null,
    horizontalScale: null,
    verticalScale: null,
    baselineShiftPx: null,
    justification: null,
    kind: "layerNameFallback",
    position: null,
    widthPx: null,
    heightPx: null,
    color: null,
    source: "layerNameFallback",
    warning: "Photoshop 无法读取 textItem/textKey，已用图层名作为可编辑文字。"
  };
}

function getTextMetadata(layer) {
  if (layer.typename !== "ArtLayer") return null;
  try {
    if (layer.kind !== LayerKind.TEXT) return null;
  } catch (e) {
    return null;
  }

  var text = null;
  try {
    text = layer.textItem;
    var contents = getStringProp(text, "contents");
    if (contents === null) throw new Error("Missing text contents.");
  } catch (e) {
    return getTextKeyMetadata(layer) || textFromLayerName(layer);
  }

  var position = null;
  try {
    position = [unitToPx(text.position[0]), unitToPx(text.position[1])];
  } catch (e) {
    position = null;
  }

  try {
    return {
      contents: contents,
      font: getStringProp(text, "font"),
      sizePx: getUnitProp(text, "size"),
      leadingPx: getUnitProp(text, "leading"),
      tracking: getStringProp(text, "tracking"),
      horizontalScale: getStringProp(text, "horizontalScale"),
      verticalScale: getStringProp(text, "verticalScale"),
      baselineShiftPx: getUnitProp(text, "baselineShift"),
      justification: getStringProp(text, "justification"),
      kind: getStringProp(text, "kind"),
      position: position,
      widthPx: getUnitProp(text, "width"),
      heightPx: getUnitProp(text, "height"),
      color: getTextColor(text),
      source: "textItem",
      warning: null
    };
  } catch (e2) {
    return getTextKeyMetadata(layer) || textFromLayerName(layer);
  }
}

function collectLayer(layer, depth, parentPath, out) {
  var name = safeString(layer.name) || "";
  var path = parentPath ? parentPath + "/" + name : name;
  var info = {
    name: name,
    path: path,
    typename: safeString(layer.typename),
    depth: depth,
    visible: !!layer.visible,
    opacity: Number(layer.opacity),
    blendMode: safeString(layer.blendMode),
    bounds: boundsToObject(layer.bounds)
  };

  try {
    info.id = layer.id;
  } catch (e) {
    info.id = null;
  }

  if (layer.typename === "ArtLayer") {
    try {
      info.kind = safeString(layer.kind);
    } catch (e) {
      info.kind = null;
    }
    info.text = getTextMetadata(layer);
  } else if (layer.typename === "LayerSet") {
    info.kind = "LayerSet";
    info.text = null;
  }

  out.push(info);

  if (layer.typename === "LayerSet") {
    for (var i = 0; i < layer.layers.length; i++) {
      collectLayer(layer.layers[i], depth + 1, path, out);
    }
  }
}

function readArgs() {
  var args = $.arguments || [];
  var psdPath = args.length > 0 ? args[0] : null;
  var outPath = args.length > 1 ? args[1] : null;
  if (!psdPath || !outPath) {
    var scriptFile = new File($.fileName);
    var argsFile = new File(scriptFile.parent.fsName + "/export-layout.args.txt");
    if (argsFile.exists && argsFile.open("r")) {
      var text = argsFile.read();
      argsFile.close();
      var lines = text.split(/\r?\n/);
      psdPath = psdPath || lines[0];
      outPath = outPath || lines[1];
    }
  }
  if (!psdPath) throw new Error("Missing PSD path argument.");
  if (!outPath) throw new Error("Missing output JSON path argument.");
  return { psdPath: psdPath, outPath: outPath };
}

function main() {
  var args = readArgs();
  var psdFile = new File(args.psdPath);
  if (!psdFile.exists) throw new Error("PSD file does not exist: " + args.psdPath);

  var doc = app.open(psdFile);
  var layers = [];
  for (var i = 0; i < doc.layers.length; i++) {
    collectLayer(doc.layers[i], 0, "", layers);
  }

  var result = {
    source: psdFile.fsName,
    exportedAt: String(new Date()),
    document: {
      name: safeString(doc.name),
      widthPx: unitToPx(doc.width),
      heightPx: unitToPx(doc.height),
      resolution: Number(doc.resolution),
      mode: safeString(doc.mode)
    },
    layerCount: layers.length,
    layers: layers
  };

  var outFile = new File(args.outPath);
  outFile.encoding = "UTF-8";
  if (!outFile.open("w")) throw new Error("Cannot open output file: " + args.outPath);
  outFile.write(toJSON(result));
  outFile.close();
  doc.close(SaveOptions.DONOTSAVECHANGES);
}

main();

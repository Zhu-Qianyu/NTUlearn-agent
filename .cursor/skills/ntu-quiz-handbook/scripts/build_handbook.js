#!/usr/bin/env node
/**
 * Build an illustrated quiz handbook .docx from outline.json + slide_snaps/meta.json.
 * Usage: node build_handbook.js outline.json
 */
const fs = require("fs");
const path = require("path");

function loadDocx() {
  const home = process.env.USERPROFILE || process.env.HOME || "";
  const candidates = [
    "docx",
    path.join(__dirname, "node_modules", "docx"),
    path.join(__dirname, "..", "..", "..", "..", "node_modules", "docx"),
    path.join(home, ".cursor", "skills", "docx", "node_modules", "docx"),
  ];
  for (const c of candidates) {
    try {
      return require(c);
    } catch (_) {}
  }
  throw new Error("Cannot require('docx'). Install it or keep the Cursor docx skill.");
}

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, LevelFormat, PageNumber, ImageRun,
} = loadDocx();

const PAGE = 11906;
const MARGIN = 850;
const CW = PAGE - MARGIN * 2;

const C = {
  navy: "1B4F72",
  blue: "2471A3",
  ink: "1C2833",
  mute: "5D6D7E",
  line: "D5D8DC",
  cream: "FDEBD0",
  pale: "EAF2F8",
  green: "145A32",
  red: "922B21",
  white: "FFFFFF",
  gold: "7D6608",
};

const font = { ascii: "Calibri", hAnsi: "Calibri", eastAsia: "微软雅黑" };
const thin = { style: BorderStyle.SINGLE, size: 4, color: C.line };
const cellB = { top: thin, bottom: thin, left: thin, right: thin };
const headerB = {
  top: { style: BorderStyle.SINGLE, size: 4, color: C.navy },
  bottom: { style: BorderStyle.SINGLE, size: 4, color: C.navy },
  left: { style: BorderStyle.SINGLE, size: 4, color: C.navy },
  right: { style: BorderStyle.SINGLE, size: 4, color: C.navy },
};

function r(text, o = {}) {
  return new TextRun({
    text: text == null ? "" : String(text),
    font,
    size: o.size || 21,
    bold: !!o.bold,
    italics: !!o.italics,
    color: o.color || C.ink,
  });
}

function p(children, o = {}) {
  const ch = typeof children === "string" ? [r(children, o)] : children;
  return new Paragraph({
    spacing: { after: o.after ?? 140, before: o.before ?? 0, line: o.line || 276 },
    alignment: o.align,
    indent: o.indent,
    keepNext: o.keepNext,
    numbering: o.numbering,
    border: o.border,
    shading: o.shading,
    children: ch,
  });
}

function rich(text, base = {}) {
  const s = text == null ? "" : String(text);
  const parts = [];
  const re = /\*\*(.+?)\*\*/g;
  let last = 0;
  let m;
  while ((m = re.exec(s))) {
    if (m.index > last) parts.push(r(s.slice(last, m.index), base));
    parts.push(r(m[1], { ...base, bold: true }));
    last = m.index + m[0].length;
  }
  if (last < s.length) parts.push(r(s.slice(last), base));
  return parts.length ? parts : [r("", base)];
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.navy, space: 4 } },
    children: [r(text, { bold: true, size: 32, color: C.navy })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 100 },
    children: [r(text, { bold: true, size: 26, color: C.blue })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 180, after: 80 },
    children: [r(text, { bold: true, size: 23, color: "1A5276" })],
  });
}

function src(text) {
  return p([
    r("出处  ", { italics: true, size: 18, color: C.gold, bold: true }),
    r(text, { italics: true, size: 18, color: C.mute }),
  ], { after: 200 });
}

function formula(text) {
  return p([new TextRun({
    text,
    font: { ascii: "Cambria Math", hAnsi: "Cambria Math", eastAsia: "Cambria Math" },
    size: 26,
    bold: true,
    color: C.navy,
  })], { align: AlignmentType.CENTER, after: 100, before: 40 });
}

function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80, line: 276 },
    children: rich(text),
  });
}

function cell(text, width, o = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    verticalAlign: VerticalAlign.TOP,
    shading: o.shading ? { type: ShadingType.CLEAR, fill: o.shading, color: "auto" } : undefined,
    borders: o.header ? headerB : cellB,
    children: [p(rich(text, {
      size: o.size || 18,
      bold: o.bold,
      color: o.color || (o.header ? C.white : C.ink),
    }), { after: 40, before: 40 })],
  });
}

function table(headers, rows, widths) {
  const w = (widths && widths.length === headers.length)
    ? widths.slice()
    : headers.map(() => Math.floor(CW / headers.length));
  const sum = w.reduce((a, b) => a + b, 0);
  if (sum !== CW) w[w.length - 1] += CW - sum;
  const head = new TableRow({
    tableHeader: true,
    cantSplit: true,
    children: headers.map((h, i) => cell(h, w[i], { header: true, shading: C.navy, bold: true })),
  });
  const bodyRows = rows.map((row, ri) => new TableRow({
    cantSplit: true,
    children: headers.map((_, i) => cell(row[i] == null ? "" : String(row[i]), w[i], {
      shading: ri % 2 ? C.pale : C.white,
    })),
  }));
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: w,
    rows: [head, ...bodyRows],
  });
}

function boxed(fill, borderColor, leftSize, kids) {
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [CW],
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CW, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill, color: "auto" },
        borders: {
          top: { style: BorderStyle.SINGLE, size: 8, color: borderColor },
          bottom: { style: BorderStyle.SINGLE, size: 8, color: borderColor },
          left: { style: BorderStyle.SINGLE, size: leftSize, color: borderColor },
          right: { style: BorderStyle.SINGLE, size: 8, color: borderColor },
        },
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        children: kids,
      })],
    })],
  });
}

function callout(title, lines) {
  return boxed(C.cream, C.red, 16, [
    p([r(title, { bold: true, size: 22, color: C.red })], { after: 80 }),
    ...lines.map((t) => p(rich(t, { size: 21 }), { after: 80 })),
  ]);
}

function note(lines) {
  return boxed(C.pale, C.blue, 12, lines.map((t) => p(rich(t, { size: 20 }), { after: 60 })));
}

function loadMeta(slidesDir) {
  const metaPath = path.join(slidesDir, "meta.json");
  if (!fs.existsSync(metaPath)) return {};
  return JSON.parse(fs.readFileSync(metaPath, "utf8"));
}

function slide(slidesDir, meta, code, page, caption) {
  const m = meta[`${code}_${page}`];
  if (!m) {
    return p([r(`（缺图 ${code} p${page}）`, { italics: true, size: 18, color: C.red })]);
  }
  const maxW = 510;
  const height = Math.round(maxW * m.h / m.w);
  const cap = `${code} 第 ${page} 页　${caption || ""}`;
  return new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [CW],
    rows: [new TableRow({
      cantSplit: true,
      children: [new TableCell({
        width: { size: CW, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: "F7F9FB", color: "auto" },
        borders: { top: thin, bottom: thin, left: thin, right: thin },
        margins: { top: 70, bottom: 70, left: 90, right: 90 },
        children: [
          p([
            r("课件截图  ", { bold: true, size: 16, color: C.blue }),
            r(cap, { size: 16, color: C.mute }),
          ], { after: 50 }),
          new Paragraph({
            alignment: AlignmentType.CENTER,
            spacing: { after: 20 },
            children: [new ImageRun({
              type: "jpg",
              data: fs.readFileSync(path.join(slidesDir, m.file)),
              transformation: { width: maxW, height },
              altText: { title: cap, description: cap, name: cap },
            })],
          }),
        ],
      })],
    })],
  });
}

function renderBlock(block, slidesDir, meta) {
  switch (block.type) {
    case "h2": return [h2(block.text || "")];
    case "h3": return [h3(block.text || "")];
    case "p": return [p(rich(block.text || ""), { after: 120 })];
    case "src": return [src(block.text || "")];
    case "formula": return [formula(block.text || "")];
    case "bullets": return (block.items || []).map(bullet);
    case "table": return [table(block.headers || [], block.rows || [], block.widths)];
    case "callout": return [callout(block.title || "课堂点名", block.lines || [])];
    case "note": return [note(block.lines || [])];
    case "slide": return [slide(slidesDir, meta, block.code, block.page, block.caption || "")];
    default:
      throw new Error(`Unknown block type: ${block.type}`);
  }
}

function slugOut(outline, outlinePath) {
  if (outline.out) return path.resolve(path.dirname(outlinePath), outline.out);
  const raw = `${outline.course || "course"}_${outline.exam || "quiz"}_备考手册_配图版.docx`;
  const safe = raw.replace(/[\\/:*?"<>|]+/g, "_");
  return path.join(path.dirname(outlinePath), safe);
}

async function main() {
  const outlinePath = path.resolve(process.argv[2] || "outline.json");
  if (!fs.existsSync(outlinePath)) {
    throw new Error(`outline not found: ${outlinePath}`);
  }
  const outline = JSON.parse(fs.readFileSync(outlinePath, "utf8"));
  const workDir = path.dirname(outlinePath);
  const slidesDir = path.resolve(workDir, outline.slidesDir || "slide_snaps");
  const meta = loadMeta(slidesDir);
  const OUT = slugOut(outline, outlinePath);

  const children = [];
  children.push(
    p([r(outline.course || "", { size: 20, color: C.mute })], { after: 80 }),
    p([r(outline.exam || "备考手册", { bold: true, size: 56, color: C.navy })], { after: 80 }),
    p([r(outline.tagline || "知识点全文 + 课件页码 + 课堂出处", { size: 24, color: C.blue })], { after: 280 }),
  );
  if (outline.meta && outline.meta.length) {
    children.push(table(["项目", "内容"], outline.meta, [2800, 7406]));
  }
  if (outline.howto && outline.howto.length) {
    children.push(p("", { after: 160 }));
    children.push(note(outline.howto));
  }
  for (const section of outline.sections || []) {
    children.push(h1(section.title || ""));
    for (const block of section.blocks || []) {
      children.push(...renderBlock(block, slidesDir, meta));
    }
  }

  const headerCourse = outline.course || "";
  const headerExam = outline.exam || "备考手册";
  const doc = new Document({
    styles: {
      default: { document: { run: { font, size: 21 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickStyle: true,
          paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 },
          run: { font, size: 32, bold: true, color: C.navy } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickStyle: true,
          paragraph: { spacing: { before: 260, after: 100 }, outlineLevel: 1 },
          run: { font, size: 26, bold: true, color: C.blue } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickStyle: true,
          paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 },
          run: { font, size: 23, bold: true, color: "1A5276" } },
      ],
    },
    numbering: {
      config: [{
        reference: "bullets",
        levels: [{
          level: 0,
          format: LevelFormat.BULLET,
          text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 420, hanging: 220 } } },
        }],
      }],
    },
    sections: [{
      properties: {
        page: {
          size: { width: PAGE, height: 16838 },
          margin: { top: 1000, bottom: 1000, left: MARGIN, right: MARGIN, header: 600, footer: 600 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.navy, space: 6 } },
            spacing: { after: 80 },
            children: [
              r(headerCourse, { size: 16, color: C.mute }),
              r("    " + headerExam, { size: 16, bold: true, color: C.navy }),
            ],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 6, color: C.line, space: 8 } },
            alignment: AlignmentType.RIGHT,
            children: [
              r("课堂回放 + 课件截图    ·    ", { size: 16, color: C.mute }),
              r("第 ", { size: 16, color: C.mute }),
              new TextRun({ children: [PageNumber.CURRENT], font, size: 16, color: C.navy, bold: true }),
              r(" 页", { size: 16, color: C.mute }),
            ],
          })],
        }),
      },
      children,
    }],
  });

  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(OUT, buf);
  console.log(JSON.stringify({ ok: true, out: OUT, bytes: buf.length }));
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});

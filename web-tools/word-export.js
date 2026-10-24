import {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Footer, PageNumber,
} from "docx";

const font = {ascii: "Arial", hAnsi: "Arial", eastAsia: "Microsoft YaHei"};
const paragraph = (text, heading) => new Paragraph({
  heading, children: [new TextRun(String(text))],
  spacing: {after: 160}, keepNext: false, keepLines: false,
});

export function speechDocument(speech, pack, material) {
  const children = [
    paragraph(speech.title, HeadingLevel.HEADING_1),
    paragraph(`${pack.motion} | ${pack.side} | ${speech.role} | ${pack.speech_time_minutes} min`),
    paragraph(pack.language === "中文" ? "发言要点" : "Speech outline", HeadingLevel.HEADING_2),
    ...speech.outline.map((line, index) => paragraph(`${index + 1}. ${line}`)),
    paragraph(pack.language === "中文" ? "发言稿" : "Debate speech", HeadingLevel.HEADING_2),
    ...speech.speech_text.split(/\n+/).filter(Boolean).map(line => paragraph(line)),
    paragraph(pack.language === "中文" ? "所选准备资料" : "Selected preparation material", HeadingLevel.HEADING_2),
  ];
  for (const section of material) {
    children.push(paragraph(section.title, HeadingLevel.HEADING_2));
    for (const line of section.text.split(/\n+/).filter(Boolean)) children.push(paragraph(line));
  }
  return new Document({
    creator: "Debate Buddy", title: speech.title,
    styles: {
      default: {document: {run: {font, size: 24}, paragraph: {keepNext: false, keepLines: false}}},
      paragraphStyles: [
        {id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: {font, size: 32, bold: true, color: "000000"},
          paragraph: {outlineLevel: 0, spacing: {before: 200, after: 180}, keepNext: false, keepLines: false}},
        {id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: {font, size: 28, bold: true, color: "000000"},
          paragraph: {outlineLevel: 1, spacing: {before: 180, after: 140}, keepNext: false, keepLines: false}},
      ],
    },
    sections: [{
      properties: {page: {size: {width: 11906, height: 16838},
        margin: {top: 1200, right: 1200, bottom: 1200, left: 1200}}},
      footers: {default: new Footer({children: [new Paragraph({
        children: [new TextRun({text: "Debate Buddy  |  ", size: 18}),
          new TextRun({children: [PageNumber.CURRENT], size: 18})],
      })]})},
      children,
    }],
  });
}

if (typeof window !== "undefined") {
  window.downloadDebateWord = async (speech, pack, material) => {
    const blob = await Packer.toBlob(speechDocument(speech, pack, material));
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = `debate-${speech.role.split(" ")[0]}.docx`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
}

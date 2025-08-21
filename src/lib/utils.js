export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return "0 Bytes";
  if (typeof bytes !== "number" || isNaN(bytes)) return "Unknown";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export function getFileTypeFromName(filename) {
  const extension = filename.split(".").pop().toLowerCase();
  const typeMap = { pdf: "pdf", txt: "txt", docx: "docx", doc: "doc" };
  return typeMap[extension] || "unknown";
}

// Client-side PDF text extraction using pdfjs-dist
// Note: This is best-effort for simple text; complex PDFs may need server-side extraction
export async function extractTextFromPdf(file) {
  const { getDocument, GlobalWorkerOptions } = await import(
    "pdfjs-dist/build/pdf"
  );
  const workerUrl = (await import("pdfjs-dist/build/pdf.worker.min.mjs?url"))
    .default;
  GlobalWorkerOptions.workerSrc = workerUrl;

  const arrayBuffer = await file.arrayBuffer();
  const loadingTask = getDocument({ data: new Uint8Array(arrayBuffer) });
  const pdf = await loadingTask.promise;
  let fullText = "";
  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum += 1) {
    const page = await pdf.getPage(pageNum);
    const content = await page.getTextContent();
    const strings = content.items.map((item) => item.str || "").filter(Boolean);
    fullText += strings.join(" ") + "\n";
  }
  return fullText.trim();
}

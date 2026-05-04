export function downloadBase64File(contentBase64: string, fileName: string, mimeType: string) {
  const link = document.createElement("a");
  link.href = `data:${mimeType};base64,${contentBase64}`;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

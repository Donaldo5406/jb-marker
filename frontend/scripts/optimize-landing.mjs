import sharp from "sharp";
import { readdir, unlink, rename } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const landingDir = path.join(__dirname, "..", "public", "landing");

const mapping = {
  "andrii-solok": "corner-tl.jpg",
  "wesley-tingey": "corner-tr.jpg",
  "hannah-busing": "corner-bl.jpg",
  "serhii-tyaglovsky": "corner-br.jpg",
  "tim-mossholder": "corner-ml.jpg",
};

const TARGET_WIDTH = 800;
const QUALITY = 82;

const files = await readdir(landingDir);

for (const file of files) {
  if (!file.endsWith(".jpg")) continue;
  if (file.startsWith("corner-")) continue;

  const matchKey = Object.keys(mapping).find((k) => file.startsWith(k));
  if (!matchKey) {
    console.log(`SKIP (no mapping): ${file}`);
    continue;
  }

  const outName = mapping[matchKey];
  const src = path.join(landingDir, file);
  const tmp = path.join(landingDir, `__tmp_${outName}`);
  const dst = path.join(landingDir, outName);

  await sharp(src)
    .resize({ width: TARGET_WIDTH, withoutEnlargement: true })
    .jpeg({ quality: QUALITY, mozjpeg: true })
    .toFile(tmp);

  await unlink(src);
  await rename(tmp, dst);

  console.log(`OK: ${file} -> ${outName}`);
}

console.log("Done.");

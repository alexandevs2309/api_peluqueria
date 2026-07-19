const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const inputDir = path.join(__dirname, 'src/assets/images');
const landingDir = path.join(inputDir, 'landing');

function convertFolder(folder) {
  fs.readdirSync(folder).forEach(file => {
    if (file.endsWith('.png')) {
      const inputPath = path.join(folder, file);
      const outputPath = path.join(folder, file.replace('.png', '.webp'));

      sharp(inputPath)
        .webp({ quality: 75 })
        .toFile(outputPath)
        .then(() => {
          console.log(`Converted: ${file}`);
        })
        .catch(err => {
          console.error(`Error converting ${file}:`, err);
        });
    }
  });
}

convertFolder(inputDir);
convertFolder(landingDir);

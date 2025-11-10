const fs = require('fs');
const path = require('path');
const { build } = require('esbuild');
const { html } = require('web-resource-inliner');

const distPath = 'dist';
const inlinedOutputPath = path.join(distPath, 'index.html');

async function bundleAndInline() {
  try {
    // 1. Bundle the JavaScript
    console.log('Bundling JavaScript with esbuild...');
    await build({
      entryPoints: ['script/main.js', 'script/index.js'],
      bundle: true,
      outdir: distPath,
      format: 'iife',
      minify: true,
    });
    console.log('JavaScript bundled successfully.');

    // 2. Modify the HTML to point to the new bundled JS file
    let htmlContent = fs.readFileSync('index.html', 'utf8');
    htmlContent = htmlContent.replace('<script type="module" src="script/main.js"></script>', `<script src="${path.join(distPath, 'main.js')}"></script>`);
    htmlContent = htmlContent.replace('<script type="module" src="script/index.js"></script>', `<script src="${path.join(distPath, 'index.js')}"></script>`);

    // 3. Inline all assets into a single HTML file
    console.log('Inlining resources...');
    html({
      fileContent: htmlContent,
      images: true,
      relativeTo: path.resolve(__dirname),
    }, (err, inlinedHtml) => {
      if (err) {
        console.error('Inlining error:', err);
      } else {
        fs.writeFileSync(inlinedOutputPath, inlinedHtml);
        console.log(`Successfully created a single file at ${inlinedOutputPath}`);
      }
    });

  } catch (err) {
    console.error('An error occurred:', err);
  }
}

if (!fs.existsSync(distPath)) {
  fs.mkdirSync(distPath);
}

bundleAndInline();
const fs = require('node:fs');
const { Resvg } = require('@resvg/resvg-js');

const svg = fs.readFileSync(process.argv[2], 'utf8');
const png = new Resvg(svg, { fitTo: { mode: 'width', value: 1024 } }).render();
fs.writeFileSync(process.argv[3], png.asPng());

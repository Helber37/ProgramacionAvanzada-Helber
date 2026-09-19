let A = 0;
let B = 0;

const width = 80;
const height = 22;
const luminance = ".,-~:;=!*#$@";

process.stdout.write("\x1b[2J");
process.stdout.write("\x1b[?25l");

function drawFrame() {
  const b = new Array(width * height).fill(" ");
  const z = new Array(width * height).fill(0);

  A += 0.07;
  B += 0.03;

  const cA = Math.cos(A);
  const sA = Math.sin(A);
  const cB = Math.cos(B);
  const sB = Math.sin(B);

  for (let j = 0; j < 6.28; j += 0.07) {
    const ct = Math.cos(j);
    const st = Math.sin(j);

    for (let i = 0; i < 6.28; i += 0.02) {
      const sp = Math.sin(i);
      const cp = Math.cos(i);
      const h = ct + 2;
      const D = 1 / (sp * h * sA + st * cA + 5);
      const t = sp * h * cA - st * sA;

      const x = (40 + 30 * D * (cp * h * cB - t * sB)) | 0;
      const y = (12 + 15 * D * (cp * h * sB + t * cB)) | 0;
      const o = x + width * y;
      const N =
        (8 *
          ((st * sA - sp * ct * cA) * cB -
            sp * ct * sA -
            st * cA -
            cp * ct * sB)) |
        0;

      if (y >= 0 && y < height && x >= 0 && x < width && D > z[o]) {
        z[o] = D;
        b[o] = luminance[N > 0 ? N : 0];
      }
    }
  }

  let output = "\x1b[H";
  for (let k = 0; k < b.length; k++) {
    output += k % width === width - 1 ? "\n" : b[k];
  }
  process.stdout.write(output);
}

const timer = setInterval(drawFrame, 50);

function cleanup() {
  clearInterval(timer);
  process.stdout.write("\x1b[?25h\n");
  process.exit(0);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);

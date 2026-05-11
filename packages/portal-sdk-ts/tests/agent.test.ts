import { strict as assert } from 'node:assert';
import { describe, it, beforeEach, afterEach } from 'node:test';
import { writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let workDir: string;
let chunks: string[];

class CaptureWriter {
  write(chunk: string): boolean {
    chunks.push(String(chunk));
    return true;
  }
}

beforeEach(() => {
  workDir = join(
    tmpdir(),
    `portal-sdk-ts-test-${Date.now()}-${Math.random().toString(36).slice(2)}`,
  );
  mkdirSync(workDir, { recursive: true });
  mkdirSync(join(workDir, 'input'), { recursive: true });
  mkdirSync(join(workDir, 'output'), { recursive: true });
  writeFileSync(join(workDir, 'params.json'), '{"x":1}');

  process.env.PARAMS_FILE = join(workDir, 'params.json');
  process.env.INPUT_DIR = join(workDir, 'input');
  process.env.OUTPUT_DIR = join(workDir, 'output');
  chunks = [];
});

afterEach(() => {
  rmSync(workDir, { recursive: true, force: true });
  delete process.env.PARAMS_FILE;
  delete process.env.INPUT_DIR;
  delete process.env.OUTPUT_DIR;
});

describe('Agent', () => {
  it('emits started on construction', async () => {
    const { Agent } = await import('../src/agent.js');
    new Agent({ writer: new CaptureWriter() });
    assert.equal(chunks.length, 1);
    const event = JSON.parse(chunks[0]!);
    assert.equal(event.type, 'started');
    assert.ok(typeof event.ts === 'string');
  });

  it('params is parsed from PARAMS_FILE', async () => {
    const { Agent } = await import('../src/agent.js');
    const a = new Agent({ writer: new CaptureWriter() });
    assert.deepEqual(a.params, { x: 1 });
  });

  it('progress clamps value', async () => {
    const { Agent } = await import('../src/agent.js');
    const a = new Agent({ writer: new CaptureWriter() });
    a.progress(1.5, 'overshoot');
    const event = JSON.parse(chunks[1]!);
    assert.equal(event.value, 1);
  });

  it('result requires file to exist', async () => {
    const { Agent } = await import('../src/agent.js');
    const a = new Agent({ writer: new CaptureWriter() });
    assert.throws(() => a.result([{ id: 'r', path: 'missing.docx' }]));
  });

  it('result accepts existing file', async () => {
    const { Agent } = await import('../src/agent.js');
    writeFileSync(join(workDir, 'output', 'report.docx'), 'fake');
    const a = new Agent({ writer: new CaptureWriter() });
    a.result([{ id: 'report', path: 'report.docx' }]);
    const last = JSON.parse(chunks[chunks.length - 1]!);
    assert.equal(last.type, 'result');
  });

  it('absolute path throws', async () => {
    const { Agent } = await import('../src/agent.js');
    const a = new Agent({ writer: new CaptureWriter() });
    assert.throws(() => a.result([{ id: 'r', path: '/tmp/abs.docx' }]));
  });

  it('cannot emit after result', async () => {
    const { Agent } = await import('../src/agent.js');
    writeFileSync(join(workDir, 'output', 'report.docx'), 'fake');
    const a = new Agent({ writer: new CaptureWriter() });
    a.result([{ id: 'r', path: 'report.docx' }]);
    assert.throws(() => a.log('info', 'late'));
  });
});

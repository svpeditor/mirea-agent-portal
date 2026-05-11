// Echo-ts агент. Самый простой пример работы с TypeScript SDK через JS.
// Использует @mirea/portal-sdk + docx-генератор через раздел Markdown
// (для simplicity без python-docx-style binding).
//
// Для production-агента команда НУГ может писать на TypeScript:
//   import { Agent } from '@mirea/portal-sdk';
// Здесь — plain JS чтобы не зависеть от tsc в runtime.

import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { Agent } from '@mirea/portal-sdk';
import { Document, Packer, Paragraph, HeadingLevel } from 'docx';

async function main() {
  const agent = new Agent();
  const params = agent.params;

  let message = String(params.message ?? '(пусто)');
  const loops = Number(params.loops ?? 5);
  const shout = Boolean(params.shout ?? false);

  if (shout) message = message.toUpperCase();

  agent.log('info', `Эхо TS: '${message}' × ${loops}`);

  const children = [
    new Paragraph({ text: 'Echo (TS)', heading: HeadingLevel.HEADING_1 }),
    new Paragraph({
      text: `Параметры: loops=${loops}, shout=${shout}`,
    }),
  ];

  for (let i = 0; i < loops; i++) {
    agent.progress((i + 1) / loops, `Строка ${i + 1} из ${loops}`);
    children.push(new Paragraph({ text: `${i + 1}. ${message}` }));
    agent.itemDone(`line-${i + 1}`, `добавлена строка ${i + 1}`);
    // Небольшая задержка чтобы прогресс был видимым.
    await new Promise((r) => setTimeout(r, 100));
  }

  const doc = new Document({ sections: [{ children }] });
  const buffer = await Packer.toBuffer(doc);

  writeFileSync(join(agent.outputDir, 'echo.docx'), buffer);

  writeFileSync(
    join(agent.outputDir, 'summary.json'),
    JSON.stringify({ message, loops, shout, runtime: 'node' }, null, 2),
    'utf-8',
  );

  agent.result([
    { id: 'report', path: 'echo.docx' },
    { id: 'summary', path: 'summary.json' },
  ]);
}

main().catch((err) => {
  console.error('agent crashed:', err);
  process.exit(1);
});

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface Props {
  content: string;
  className?: string;
}

const PROSE = [
  'space-y-4 leading-relaxed',
  '[&_h2]:font-serif [&_h2]:text-2xl [&_h2]:mt-6',
  '[&_h3]:font-serif [&_h3]:text-xl [&_h3]:mt-4',
  '[&_a]:text-[color:var(--color-accent)] [&_a]:underline',
  '[&_code]:bg-[color:var(--color-bg-tertiary)] [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm [&_code]:font-mono',
  '[&_pre]:bg-[color:var(--color-bg-tertiary)] [&_pre]:p-3 [&_pre]:rounded [&_pre]:overflow-x-auto',
  '[&_ul]:list-disc [&_ul]:pl-6',
  '[&_ol]:list-decimal [&_ol]:pl-6',
].join(' ');

export function Markdown({ content, className }: Props) {
  return (
    <div className={cn(PROSE, className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

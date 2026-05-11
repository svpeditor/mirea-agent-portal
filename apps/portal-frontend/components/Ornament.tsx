/**
 * Editorial ornaments — fleurons, asterisms, paragraph marks used as
 * section dividers and decorative inline marks. Renders into a flex row
 * with double-rule lines on either side, ornament centered.
 *
 * Variants:
 *  - 'fleuron' (❦)   — between major sections
 *  - 'asterism' (⁂)   — between sub-sections
 *  - 'pilcrow' (§)    — like masthead emblem
 *  - 'three' (✦ ✦ ✦) — heavier divider, end of chapter
 */
import { cn } from '@/lib/utils';

const GLYPH = {
  fleuron: '❦',
  asterism: '⁂',
  pilcrow: '§',
  three: '✦ ✦ ✦',
  bullet: '·',
} as const;

type Variant = keyof typeof GLYPH;

interface Props {
  variant?: Variant;
  className?: string;
  /** show flanking double-rule lines */
  rules?: boolean;
}

export function Ornament({ variant = 'fleuron', className, rules = true }: Props) {
  if (!rules) {
    return (
      <span className={cn('ed-ornament inline-block', className)} aria-hidden>
        {GLYPH[variant]}
      </span>
    );
  }
  return (
    <div
      className={cn(
        'flex items-center justify-center gap-6 py-6',
        className,
      )}
      aria-hidden
    >
      <span className="block h-px flex-1 max-w-[12rem] bg-[color:var(--color-text-primary)] opacity-50" />
      <span className="ed-ornament ed-anim-bleed text-2xl">
        {GLYPH[variant]}
      </span>
      <span className="block h-px flex-1 max-w-[12rem] bg-[color:var(--color-text-primary)] opacity-50" />
    </div>
  );
}

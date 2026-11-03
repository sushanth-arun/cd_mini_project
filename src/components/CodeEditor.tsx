import { useRef } from 'react';
import { FileCode, Hash } from 'lucide-react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
}

function CodeEditor({ value, onChange }: CodeEditorProps) {
  const lineCount = value.split('\n').length;
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);

  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[540px]">
          {/* Editor Header Bar */}
          <div className="bg-slate-900 px-4 py-2.5 flex items-center justify-between border-b border-slate-800">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-blue-400" />
              <span className="text-white text-sm font-mono font-medium">main.c</span>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 font-mono">C99</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1">
                <Hash className="w-3.5 h-3.5 text-slate-500" />
                {lineCount} lines
              </span>
              <span>{value.length} chars</span>
            </div>
          </div>

          {/* Editor Body with Line Numbers */}
          <div className="flex-1 flex overflow-hidden bg-slate-950 font-mono text-sm relative">
            {/* Line Numbers Column */}
            <div
              ref={lineNumbersRef}
              className="w-12 py-3 px-2 text-right bg-slate-900 text-slate-500 select-none overflow-hidden border-r border-slate-800 font-mono text-xs leading-6"
            >
              {Array.from({ length: Math.max(lineCount, 1) }).map((_, i) => (
                <div key={i} className="h-6">
                  {i + 1}
                </div>
              ))}
            </div>

            {/* Text Area */}
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onScroll={handleScroll}
              className="flex-1 p-3 bg-slate-950 text-slate-100 resize-none focus:outline-none font-mono text-sm leading-6 selection:bg-blue-600/40 tab-size-4"
              spellCheck={false}
              placeholder="// Enter your C code here..."
              style={{ tabSize: 4 }}
            />
          </div>
        </div>
        );
}

        export default CodeEditor;

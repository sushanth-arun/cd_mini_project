interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
}

function CodeEditor({ value, onChange }: CodeEditorProps) {
  return (
    <div className="bg-white rounded-lg border border-blue-200 shadow-sm overflow-hidden">
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-4 py-2">
        <span className="text-white text-sm font-medium">main.c</span>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-[500px] p-4 font-mono text-sm bg-gray-50 text-gray-900 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset"
        spellCheck={false}
        placeholder="Enter your C code here..."
      />
    </div>
  );
}

export default CodeEditor;

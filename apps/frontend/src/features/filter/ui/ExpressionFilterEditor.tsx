import Editor, { type OnMount } from '@monaco-editor/react';

interface SchemaColumn {
  name: string;
  type: string;
}

interface Props {
  schema: SchemaColumn[];
  value: { expr: string };
  onChange: (v: { expr: string }) => void;
}

const KEYWORDS = ['AND', 'OR', 'NOT', 'TRUE', 'FALSE', 'NULL'];

export function ExpressionFilterEditor({ schema, value, onChange }: Props) {
  const handleMount: OnMount = (_editor, monaco) => {
    // Register the SQL-ish language once per monaco instance.
    if (!monaco.languages.getLanguages().some(l => l.id === 'fna-expr')) {
      monaco.languages.register({ id: 'fna-expr' });
      monaco.languages.setMonarchTokensProvider('fna-expr', {
        keywords: KEYWORDS,
        tokenizer: {
          root: [
            [/[A-Za-z_][A-Za-z0-9_]*/, {
              cases: { '@keywords': 'keyword', '@default': 'identifier' },
            }],
            [/'[^']*'/, 'string'],
            [/\d+(\.\d+)?/, 'number'],
            [/[=<>!]+/, 'operator'],
          ],
        },
      });
    }
    monaco.languages.registerCompletionItemProvider('fna-expr', {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };
        return {
          suggestions: [
            ...schema.map(c => ({
              label: c.name,
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: c.name,
              detail: c.type,
              range,
            })),
            ...KEYWORDS.map(kw => ({
              label: kw,
              kind: monaco.languages.CompletionItemKind.Keyword,
              insertText: kw,
              range,
            })),
          ],
        };
      },
    });
  };

  return (
    <div className="expression-editor">
      <Editor
        height="180px"
        language="fna-expr"
        theme="vs-light"
        value={value.expr}
        onMount={handleMount}
        onChange={(v) => onChange({ expr: v ?? '' })}
        options={{ minimap: { enabled: false }, fontSize: 14 }}
      />
      <div className="hint" style={{ fontSize: 12, color: '#666' }}>
        e.g. <code>age &gt; 18 AND country = 'IN'</code>
      </div>
    </div>
  );
}

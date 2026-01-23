import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import { Bold, Italic, Underline as UnderlineIcon, List, ListOrdered } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

const MenuBar = ({ editor }) => {
  if (!editor) return null;

  return (
    <div className="flex items-center gap-1 p-2 border-b border-white/10 bg-[#1E1E1E] rounded-t-lg">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={cn(
          'h-8 w-8 p-0',
          editor.isActive('bold') ? 'bg-[#007AFF]/20 text-[#007AFF]' : 'text-gray-400 hover:text-white hover:bg-white/10'
        )}
      >
        <Bold className="w-4 h-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={cn(
          'h-8 w-8 p-0',
          editor.isActive('italic') ? 'bg-[#007AFF]/20 text-[#007AFF]' : 'text-gray-400 hover:text-white hover:bg-white/10'
        )}
      >
        <Italic className="w-4 h-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        className={cn(
          'h-8 w-8 p-0',
          editor.isActive('underline') ? 'bg-[#007AFF]/20 text-[#007AFF]' : 'text-gray-400 hover:text-white hover:bg-white/10'
        )}
      >
        <UnderlineIcon className="w-4 h-4" />
      </Button>
      <div className="w-px h-5 bg-white/10 mx-1" />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={cn(
          'h-8 w-8 p-0',
          editor.isActive('bulletList') ? 'bg-[#007AFF]/20 text-[#007AFF]' : 'text-gray-400 hover:text-white hover:bg-white/10'
        )}
      >
        <List className="w-4 h-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={cn(
          'h-8 w-8 p-0',
          editor.isActive('orderedList') ? 'bg-[#007AFF]/20 text-[#007AFF]' : 'text-gray-400 hover:text-white hover:bg-white/10'
        )}
      >
        <ListOrdered className="w-4 h-4" />
      </Button>
    </div>
  );
};

const RichTextEditor = ({ 
  value = '', 
  onChange, 
  placeholder = 'Start typing...', 
  disabled = false,
  className = '',
  'data-testid': dataTestId 
}) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        horizontalRule: false,
      }),
      Underline,
    ],
    content: value,
    editable: !disabled,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      if (onChange) {
        onChange(html);
      }
    },
    editorProps: {
      attributes: {
        class: 'prose prose-invert prose-sm max-w-none focus:outline-none min-h-[200px] p-4',
        'data-testid': dataTestId,
      },
    },
  });

  // Update content when value changes externally
  React.useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || '');
    }
  }, [value, editor]);

  // Update editable state
  React.useEffect(() => {
    if (editor) {
      editor.setEditable(!disabled);
    }
  }, [disabled, editor]);

  return (
    <div className={cn('rounded-lg border border-white/10 overflow-hidden', className)}>
      {!disabled && <MenuBar editor={editor} />}
      <div className="bg-[#121212] min-h-[200px]">
        <EditorContent 
          editor={editor} 
          className="[&_.ProseMirror]:min-h-[200px] [&_.ProseMirror]:p-4 [&_.ProseMirror]:text-white [&_.ProseMirror_p.is-editor-empty:first-child::before]:text-gray-500 [&_.ProseMirror_p.is-editor-empty:first-child::before]:content-[attr(data-placeholder)] [&_.ProseMirror_p.is-editor-empty:first-child::before]:float-left [&_.ProseMirror_p.is-editor-empty:first-child::before]:h-0 [&_.ProseMirror_p.is-editor-empty:first-child::before]:pointer-events-none"
        />
      </div>
    </div>
  );
};

export default RichTextEditor;

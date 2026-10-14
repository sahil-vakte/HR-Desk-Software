import { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Box, Button, Stack, Typography } from '@mui/material';
export default function RichText({ label, value, onChange, error }) {
  const editor = useEditor({ extensions: [StarterKit], content: value || '', onUpdate: ({ editor }) => onChange(editor.getHTML()), editorProps: { attributes: { 'aria-label': label, role: 'textbox' } } });
  useEffect(() => { if (editor && editor.getHTML() !== (value || '') && !editor.isFocused) editor.commands.setContent(value || ''); }, [value, editor]);
  return <Box sx={{ border: 1, borderColor: error ? 'error.main' : 'divider', borderRadius: 1, p: 2 }}>
    <Typography variant="body2">{label}</Typography><Stack direction="row"><Button onClick={() => editor?.chain().focus().toggleBold().run()}>Bold</Button><Button onClick={() => editor?.chain().focus().toggleItalic().run()}>Italic</Button><Button onClick={() => editor?.chain().focus().toggleBulletList().run()}>List</Button></Stack>
    <Box sx={{ '& .tiptap': { minHeight: 100, outline: 'none' } }}><EditorContent editor={editor} /></Box>
    {error && <Typography color="error" variant="caption">{error}</Typography>}
  </Box>;
}

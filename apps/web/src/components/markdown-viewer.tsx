import ReactMarkdown from 'react-markdown';

type MarkdownViewerProps = {
  markdown: string;
};

export function MarkdownViewer({ markdown }: MarkdownViewerProps) {
  return <ReactMarkdown>{markdown}</ReactMarkdown>;
}

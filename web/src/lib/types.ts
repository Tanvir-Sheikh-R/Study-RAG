export type SubChapter = {
  name: string;
  number: number | string | null;
  starting_page: number | null;
  writer_name: string | null;
};

export type Chapter = {
  name: string;
  chapter_name: string;
  number: number | string | null;
  starting_page: number | null;
  sub_chapters: SubChapter[];
};

export type Subject = {
  subject: string;
  stream: string | null;
  label: string;
  book: string;
  indexed: boolean;
  chapters: Chapter[];
};

export type ClassNode = {
  class_id: string;
  label: string;
  nested: boolean;
  subjects: Subject[];
};

export type TreeCounts = {
  classes: number;
  subjects: number;
  chapters: number;
  indexed_books: number;
};

export type TreeResponse = {
  classes: ClassNode[];
  counts: TreeCounts;
};

export type ChapterContext = {
  class_id: string;
  class_label: string;
  subject: string;
  subject_label: string;
  stream: string | null;
  book: string;
  chapter: string;
};

export type Source = {
  chapter: string | null;
  part: string | null;
  writer_name: string | null;
  page_start: number | null;
  page_end: number | null;
  snippet: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  created_at: string;
};

export type ThreadSummary = {
  thread_id: string;
  title: string;
  context: Partial<ChapterContext>;
  message_count: number;
  preview: string;
  created_at: string;
  updated_at: string;
};

export type ThreadGroup = {
  label: string;
  threads: ThreadSummary[];
};

export type ThreadDetail = {
  thread_id: string;
  title: string;
  context: Partial<ChapterContext>;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
};

export type Health = {
  status: "ok";
  embedding_model: string;
  device: string;
  dimension: number;
  indexed_books: number;
  named_books: number;
  llm_model: string;
};

export type StreamStatus = "searching" | "answering";

export type StreamEvent =
  | { type: "status"; stage: StreamStatus; message: string }
  | { type: "sources"; sources: Source[]; warning: string | null }
  | { type: "delta"; text: string }
  | { type: "done"; thread_id: string; title: string; updated_at: string }
  | { type: "error"; message: string };

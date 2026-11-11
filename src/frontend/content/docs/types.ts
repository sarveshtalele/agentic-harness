// Documentation pages. Each page is Markdown; ## headings fill the "On this page" list.
export type DocPage = { slug: string; title: string; summary: string; body: string };
export type DocGroup = { title: string; pages: DocPage[] };

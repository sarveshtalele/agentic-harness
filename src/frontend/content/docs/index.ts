import { architecture } from "./architecture";
import { features } from "./features";
import { getStarted } from "./getStarted";
import { govern } from "./govern";
import { reference } from "./reference";
import type { DocGroup } from "./types";

export type { DocGroup, DocPage } from "./types";

export const groups: DocGroup[] = [getStarted, features, govern, reference, architecture];

export const pages = groups.flatMap((group) => group.pages.map((page) => ({ ...page, group: group.title })));

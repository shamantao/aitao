CREATE TABLE IF NOT EXISTS "users" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "createdAt" TEXT NOT NULL DEFAULT (datetime('now')),
    "metadata" TEXT
);

CREATE TABLE IF NOT EXISTS "threads" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdAt" TEXT NOT NULL DEFAULT (datetime('now')),
    "name" TEXT,
    "userId" TEXT,
    "userIdentifier" TEXT,
    "tags" TEXT,
    "metadata" TEXT,
    FOREIGN KEY ("userId") REFERENCES "users" ("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "steps" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "parentId" TEXT,
    "disableFeedback" INTEGER NOT NULL DEFAULT 0,
    "streaming" INTEGER NOT NULL DEFAULT 0,
    "waitForAnswer" INTEGER DEFAULT 0,
    "isError" INTEGER DEFAULT 0,
    "metadata" TEXT,
    "tags" TEXT,
    "input" TEXT,
    "output" TEXT,
    "createdAt" TEXT DEFAULT (datetime('now')),
    "start" TEXT,
    "end" TEXT,
    "generation" TEXT,
    "showInput" TEXT,
    "language" TEXT,
    "indent" INTEGER,
    "defaultOpen" INTEGER DEFAULT 0,
    FOREIGN KEY ("threadId") REFERENCES "threads" ("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "elements" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "threadId" TEXT,
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INTEGER,
    "mime" TEXT,
    "forId" TEXT,
    FOREIGN KEY ("threadId") REFERENCES "threads" ("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "feedbacks" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "forId" TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "value" INTEGER NOT NULL,
    "comment" TEXT,
    "strategy" TEXT NOT NULL,
    FOREIGN KEY ("threadId") REFERENCES "threads" ("id") ON DELETE CASCADE
);

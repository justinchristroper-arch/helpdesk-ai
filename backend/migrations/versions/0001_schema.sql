CREATE TABLE documents (
	id VARCHAR(36) NOT NULL,
	title VARCHAR(200) NOT NULL,
	filename VARCHAR(255) NOT NULL,
	mime_type VARCHAR(100) NOT NULL,
	status VARCHAR(20) NOT NULL,
	embedding_model VARCHAR(150) NOT NULL,
	content_hash VARCHAR(64),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id)
)

;

CREATE TABLE users (
	id VARCHAR(36) NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash TEXT NOT NULL,
	role VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
)

;

CREATE TABLE conversations (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	title VARCHAR(120) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE document_chunks (
	id VARCHAR(36) NOT NULL,
	document_id VARCHAR(36) NOT NULL,
	chunk_index INTEGER NOT NULL,
	page_number INTEGER,
	section TEXT,
	content TEXT NOT NULL,
	embedding VECTOR(1536) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)

;

CREATE TABLE messages (
	id VARCHAR(36) NOT NULL,
	conversation_id VARCHAR(36) NOT NULL,
	role VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	outcome VARCHAR(30),
	model VARCHAR(150),
	prompt_version VARCHAR(30),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(conversation_id) REFERENCES conversations (id)
)

;

CREATE TABLE feedback (
	id VARCHAR(36) NOT NULL,
	message_id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	rating INTEGER NOT NULL,
	note TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (message_id, user_id),
	FOREIGN KEY(message_id) REFERENCES messages (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE message_sources (
	id VARCHAR(36) NOT NULL,
	message_id VARCHAR(36) NOT NULL,
	chunk_id VARCHAR(36),
	document_id VARCHAR(36) NOT NULL,
	title TEXT NOT NULL,
	section TEXT,
	page_number INTEGER,
	excerpt TEXT NOT NULL,
	relevance_score DOUBLE PRECISION NOT NULL,
	citation_number INTEGER,
	PRIMARY KEY (id),
	FOREIGN KEY(message_id) REFERENCES messages (id),
	FOREIGN KEY(chunk_id) REFERENCES document_chunks (id) ON DELETE SET NULL
)

;
CREATE INDEX ix_conversations_user_id ON conversations (user_id);
CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id);
CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);
CREATE INDEX ix_message_sources_message_id ON message_sources (message_id);

-- =====================================================================
-- AyurVeda RAG Prototype: Database Cleanup & Maintenance Script
-- =====================================================================
-- This script fixes corrupted, split, duplicate, or empty database entries
-- caused by prior frontend race conditions and state closure bugs.
-- Run this script once in your Supabase project's SQL Editor.
-- =====================================================================

-- 1. Remove empty conversations (conversations with 0 messages)
-- These were created when frontend race conditions failed foreign key / RLS checks.
DELETE FROM public.conversations
WHERE id NOT IN (
  SELECT DISTINCT conversation_id FROM public.messages
);

-- 2. Clean up orphaned assistant-only conversations
-- These occurred when new chats generated a second conversation ID for the assistant response.
DELETE FROM public.conversations
WHERE id NOT IN (
  SELECT DISTINCT conversation_id FROM public.messages WHERE role = 'user'
);

-- 3. Remove accidental duplicate identical consecutive messages within 5 seconds
DELETE FROM public.messages m1
WHERE EXISTS (
  SELECT 1 FROM public.messages m2
  WHERE m2.conversation_id = m1.conversation_id
    AND m2.role = m1.role
    AND m2.content = m1.content
    AND m2.id < m1.id
    AND (m1.created_at - m2.created_at) < interval '5 seconds'
);

-- 4. Ensure optimized composite index exists for ordered message retrieval
CREATE INDEX IF NOT EXISTS messages_conversation_created_id_idx 
ON public.messages (conversation_id, created_at ASC, id ASC);

-- 5. Helper function for periodic automatic cleanup of empty conversations
CREATE OR REPLACE FUNCTION public.cleanup_empty_conversations()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  deleted_count integer;
BEGIN
  DELETE FROM public.conversations
  WHERE id NOT IN (
    SELECT DISTINCT conversation_id FROM public.messages
  );
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.cleanup_empty_conversations() FROM public, anon;
GRANT EXECUTE ON FUNCTION public.cleanup_empty_conversations() TO authenticated;


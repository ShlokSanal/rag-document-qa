"""Supabase authentication and per-user conversation storage."""

import os

import streamlit as st
from supabase import Client, create_client


def setting(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except (KeyError, FileNotFoundError):
        value = None
    return value or os.getenv(name)


def configured() -> bool:
    return bool(setting("SUPABASE_URL") and setting("SUPABASE_KEY"))


def create_supabase_client() -> Client:
    return create_client(setting("SUPABASE_URL"), setting("SUPABASE_KEY"))


def set_user_session(client: Client) -> None:
    access = st.session_state.get("sb_access_token")
    refresh = st.session_state.get("sb_refresh_token")
    if access and refresh:
        session = client.auth.set_session(access, refresh).session
        st.session_state["sb_access_token"] = session.access_token
        st.session_state["sb_refresh_token"] = session.refresh_token


def save_auth_session(session) -> None:
    st.session_state["sb_access_token"] = session.access_token
    st.session_state["sb_refresh_token"] = session.refresh_token
    st.session_state["sb_user_id"] = session.user.id
    st.session_state["sb_email"] = session.user.email


def clear_auth_session() -> None:
    for key in ("sb_access_token", "sb_refresh_token", "sb_user_id", "sb_email", "active_conversation"):
        st.session_state.pop(key, None)


def list_conversations(client: Client) -> list[dict]:
    return (
        client.table("conversations")
        .select("id, title, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
    )


def create_conversation(client: Client, user_id: str) -> dict:
    return (
        client.table("conversations")
        .insert({"user_id": user_id, "title": "New chat"})
        .select("id, title, created_at")
        .single()
        .execute()
        .data
    )


def load_messages(client: Client, conversation_id: str) -> list[dict]:
    return (
        client.table("messages")
        .select("id, role, content, sources, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
        .data
    )


def save_message(client: Client, conversation_id: str, user_id: str, role: str, content: str, sources=None) -> None:
    client.table("messages").insert({
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "sources": sources or [],
    }).execute()


def update_title(client: Client, conversation_id: str, title: str) -> None:
    client.table("conversations").update({"title": title[:80]}).eq("id", conversation_id).execute()

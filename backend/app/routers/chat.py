from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..auth import get_current_user, UserContext
from ..agent import run_agent
from ..tools.actions import execute as execute_action

router = APIRouter(tags=["chat"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ConfirmActionRequest(BaseModel):
    action_type: str
    details: dict
    reason: Optional[str] = ""


@router.post("/")
def chat(req: ChatRequest, user: UserContext = Depends(get_current_user)):
    """Main chat endpoint — runs the multi-step agent."""
    import sys
    print(f"[CHAT DEBUG] user={user.username} account_id={user.account_id} is_customer={user.is_customer}", flush=True, file=sys.stderr)
    messages = [m.model_dump() for m in req.messages]
    result = run_agent(messages=messages, user=user)
    print(f"[CHAT DEBUG] tool_calls={[tc['tool'] for tc in result.get('tool_calls', [])]}", flush=True, file=sys.stderr)
    for tc in result.get('tool_calls', []):
        print(f"[CHAT DEBUG]   {tc['tool']} input={tc['input']} found={tc['output'].get('found')}", flush=True, file=sys.stderr)
    return result


# Also handle without trailing slash (some proxies strip it)
@router.post("")
def chat_no_slash(req: ChatRequest, user: UserContext = Depends(get_current_user)):
    """Main chat endpoint — alias without trailing slash."""
    import sys
    print(f"[CHAT DEBUG no-slash] user={user.username} account_id={user.account_id}", flush=True, file=sys.stderr)
    messages = [m.model_dump() for m in req.messages]
    result = run_agent(messages=messages, user=user)
    return result


@router.post("/confirm")
def confirm_action(req: ConfirmActionRequest, user: UserContext = Depends(get_current_user)):
    """Execute a previously prepared action after user confirmation."""
    result = execute_action(
        action_type=req.action_type,
        details=req.details,
        reason=req.reason,
        user=user,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Action failed"))
    return result

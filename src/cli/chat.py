"""
CLI Chat Module for AItao.

Provides an interactive command-line interface for chatting with the LLM,
with automatic RAG context enrichment from indexed documents.

Features:
- Interactive multi-turn conversations
- RAG context display for debugging
- Conversation history saving
- Streaming responses
- Color-coded output

Usage:
    python -m src.cli.chat
    # or via aitao.sh:
    ./aitao.sh chat
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import ConfigManager, get_config
from src.core.logger import get_logger
from src.core.pathmanager import path_manager
from src.llm.ollama_client import (
    OllamaClient,
    OllamaChatMessage,
    OllamaConnectionError,
    OllamaModelNotFound,
)
from src.llm.rag_engine import RAGEngine

logger = get_logger("cli.chat")


# ============================================================================
# Terminal Colors
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Background
    BG_BLUE = "\033[44m"
    
    @classmethod
    def disable(cls):
        """Disable colors (for non-TTY output)."""
        for attr in dir(cls):
            if not attr.startswith('_') and attr.isupper():
                setattr(cls, attr, "")


# Disable colors if not in TTY
if not sys.stdout.isatty():
    Colors.disable()


# ============================================================================
# Chat Session
# ============================================================================

class ChatSession:
    """
    Manages an interactive chat session with RAG-enhanced LLM.
    
    Handles:
    - Message history
    - RAG context enrichment
    - Streaming responses
    - History persistence
    """
    
    def __init__(
        self,
        config: ConfigManager = None,
        model: str = None,
        show_context: bool = True,
        save_history: bool = True,
    ):
        """
        Initialize chat session.
        
        Args:
            config: Configuration manager instance
            model: Model name to use (default from config)
            show_context: Whether to display RAG context documents
            save_history: Whether to save conversation to file
        """
        self.config = config or get_config()
        self.logger = get_logger("cli.chat")
        
        # Initialize clients
        self.ollama = OllamaClient(self.config, self.logger)
        self.rag = RAGEngine(self.config, self.logger)
        
        # Settings
        self.model = model or self.config.get(
            "llm.ollama.default_model", "qwen2.5-coder:7b"
        )
        self.show_context = show_context
        self.save_history = save_history
        
        # Conversation state
        self.messages: List[Dict[str, str]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        
        # History file
        self.history_dir = path_manager.get_storage_root() / "history" / "chat"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_dir / f"chat_{self.session_id}.json"
    
    def add_system_message(self, content: str):
        """Add a system message to the conversation."""
        self.messages.append({"role": "system", "content": content})
    
    def chat(self, user_input: str) -> str:
        """
        Send a message and get a response.
        
        Args:
            user_input: User's message
            
        Returns:
            Assistant's response text
        """
        # Add user message
        self.messages.append({"role": "user", "content": user_input})
        
        # Enrich with RAG context
        enriched_messages, context_docs, context_text = self.rag.enrich_messages(
            self.messages
        )
        
        # Display context if enabled
        if self.show_context and context_docs:
            self._display_context(context_docs)
        
        # Convert to Ollama format
        ollama_messages = [
            OllamaChatMessage(role=m["role"], content=m["content"])
            for m in enriched_messages
        ]
        
        # Stream response
        response_text = self._stream_response(ollama_messages)
        
        # Add assistant response to history
        self.messages.append({"role": "assistant", "content": response_text})
        
        # Save history
        if self.save_history:
            self._save_history()
        
        return response_text
    
    def _stream_response(self, messages: List[OllamaChatMessage]) -> str:
        """Stream response from LLM and display in real-time."""
        full_response = ""
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}Assistant:{Colors.RESET} ", end="", flush=True)
        
        try:
            for chunk in self.ollama.chat(
                messages=messages,
                model=self.model,
                stream=True,
            ):
                # Parse JSON chunk
                try:
                    data = json.loads(chunk)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        print(content, end="", flush=True)
                        full_response += content
                    
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
                    
        except OllamaConnectionError as e:
            error_msg = f"\n{Colors.RED}Error: Cannot connect to Ollama - {e}{Colors.RESET}"
            print(error_msg)
            return f"[Error: {e}]"
        except OllamaModelNotFound as e:
            error_msg = f"\n{Colors.RED}Error: Model not found - {e}{Colors.RESET}"
            print(error_msg)
            return f"[Error: {e}]"
        
        print()  # Newline after response
        return full_response
    
    def _display_context(self, context_docs):
        """Display RAG context documents used."""
        if not context_docs:
            return
        
        print(f"\n{Colors.DIM}{'─' * 60}")
        print(f"📚 RAG Context ({len(context_docs)} documents):")
        
        for i, doc in enumerate(context_docs, 1):
            score = f"{doc.score:.2f}" if doc.score else "N/A"
            path = doc.path or doc.id
            # Truncate path if too long
            if len(path) > 50:
                path = "..." + path[-47:]
            print(f"   {i}. [{score}] {path}")
        
        print(f"{'─' * 60}{Colors.RESET}")
    
    def _save_history(self):
        """Save conversation history to JSON file."""
        try:
            history_data = {
                "session_id": self.session_id,
                "model": self.model,
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "messages": self.messages,
            }
            
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"Failed to save history: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "session_id": self.session_id,
            "model": self.model,
            "message_count": len(self.messages),
            "duration_seconds": time.time() - self.start_time,
            "history_file": str(self.history_file) if self.save_history else None,
        }


# ============================================================================
# Interactive CLI
# ============================================================================

def print_welcome(model: str):
    """Print welcome message."""
    print(f"""
{Colors.BLUE}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║                    ☯️  AItao Chat                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.DIM}Model: {model}
Commands:
  /quit, /exit, /q  - Exit chat
  /clear            - Clear conversation history
  /context on|off   - Toggle RAG context display
  /stats            - Show session statistics
  /help             - Show this help{Colors.RESET}
""")


def print_help():
    """Print help message."""
    print(f"""
{Colors.BOLD}Available Commands:{Colors.RESET}
  /quit, /exit, /q  - Exit the chat session
  /clear            - Clear conversation history and start fresh
  /context on       - Show RAG context documents (default: on)
  /context off      - Hide RAG context documents
  /stats            - Display session statistics
  /model <name>     - Switch to a different model
  /history          - Show conversation history
  /help, /?         - Show this help message

{Colors.BOLD}Tips:{Colors.RESET}
  • Press Ctrl+C to interrupt a response
  • Press Ctrl+D to exit
  • Conversations are saved to {Colors.DIM}data/history/chat/{Colors.RESET}
""")


def run_interactive_chat(
    model: str = None,
    show_context: bool = True,
    save_history: bool = True,
):
    """
    Run the interactive chat loop.
    
    Args:
        model: Model name to use
        show_context: Whether to show RAG context
        save_history: Whether to save conversation history
    """
    try:
        session = ChatSession(
            model=model,
            show_context=show_context,
            save_history=save_history,
        )
    except Exception as e:
        print(f"{Colors.RED}Error initializing chat session: {e}{Colors.RESET}")
        return 1
    
    print_welcome(session.model)
    
    try:
        while True:
            try:
                # Get user input
                user_input = input(f"\n{Colors.GREEN}{Colors.BOLD}You:{Colors.RESET} ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input.lower().split()
                    command = cmd[0]
                    args = cmd[1:] if len(cmd) > 1 else []
                    
                    if command in ("/quit", "/exit", "/q"):
                        print(f"\n{Colors.DIM}Goodbye! 👋{Colors.RESET}")
                        break
                    
                    elif command == "/clear":
                        session.messages.clear()
                        print(f"{Colors.YELLOW}Conversation cleared.{Colors.RESET}")
                        continue
                    
                    elif command == "/context":
                        if args and args[0] == "off":
                            session.show_context = False
                            print(f"{Colors.YELLOW}RAG context display disabled.{Colors.RESET}")
                        else:
                            session.show_context = True
                            print(f"{Colors.YELLOW}RAG context display enabled.{Colors.RESET}")
                        continue
                    
                    elif command == "/stats":
                        stats = session.get_stats()
                        print(f"\n{Colors.BOLD}Session Statistics:{Colors.RESET}")
                        print(f"  Session ID: {stats['session_id']}")
                        print(f"  Model: {stats['model']}")
                        print(f"  Messages: {stats['message_count']}")
                        print(f"  Duration: {stats['duration_seconds']:.1f}s")
                        if stats['history_file']:
                            print(f"  History: {stats['history_file']}")
                        continue
                    
                    elif command == "/model":
                        if args:
                            session.model = args[0]
                            print(f"{Colors.YELLOW}Switched to model: {session.model}{Colors.RESET}")
                        else:
                            print(f"Current model: {session.model}")
                        continue
                    
                    elif command == "/history":
                        print(f"\n{Colors.BOLD}Conversation History:{Colors.RESET}")
                        for i, msg in enumerate(session.messages):
                            role = msg["role"].capitalize()
                            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                            print(f"  {i+1}. [{role}] {content}")
                        continue
                    
                    elif command in ("/help", "/?"):
                        print_help()
                        continue
                    
                    else:
                        print(f"{Colors.YELLOW}Unknown command: {command}. Type /help for available commands.{Colors.RESET}")
                        continue
                
                # Regular chat message
                session.chat(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Colors.DIM}(Interrupted){Colors.RESET}")
                continue
                
    except EOFError:
        print(f"\n{Colors.DIM}Goodbye! 👋{Colors.RESET}")
    
    # Print final stats
    stats = session.get_stats()
    print(f"\n{Colors.DIM}Session ended: {stats['message_count']} messages in {stats['duration_seconds']:.1f}s{Colors.RESET}")
    
    return 0


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for CLI chat."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AItao Interactive Chat with RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli.chat
  python -m src.cli.chat --model llama3.1:8b
  python -m src.cli.chat --no-context
        """,
    )
    
    parser.add_argument(
        "-m", "--model",
        help="Model name to use (default: from config)",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Hide RAG context documents",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Don't save conversation history",
    )
    
    args = parser.parse_args()
    
    return run_interactive_chat(
        model=args.model,
        show_context=not args.no_context,
        save_history=not args.no_history,
    )


if __name__ == "__main__":
    sys.exit(main())

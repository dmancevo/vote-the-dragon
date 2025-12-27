# Claude Developer Guide

This document provides context for AI assistants working on the Dragonseeker codebase.

## Project Overview

**Dragonseeker** is a real-time multiplayer social deduction game built with FastAPI, HTMX, Tailwind CSS, and DaisyUI.

### Tech Stack

- **Backend**: FastAPI 0.118.0 + WebSockets
- **Frontend**: HTMX 2.0.4 + Tailwind CSS + DaisyUI 4.12
- **Templates**: Jinja2 3.1.6
- **Package Manager**: uv (Astral)
- **Testing**: pytest + pytest-asyncio
- **Linting**: ruff (formatting + linting)
- **Type Checking**: ty (by Astral)

## Project Structure

```
app/
├── app.py                      # Main FastAPI application with lifespan events
├── pyproject.toml             # Project dependencies and tool configuration
├── core/                      # Core game logic
│   ├── constants.py          # Game settings, MIN_PLAYERS=3, MAX_PLAYERS=12, WORD_PAIRS
│   ├── player.py             # Player model with id, nickname, role, is_alive, is_host
│   ├── roles.py              # Role assignment logic (DRAGON, KNIGHT, VILLAGER)
│   ├── game_session.py       # Game state machine (LOBBY → PLAYING → VOTING → DRAGON_GUESS → FINISHED)
│   └── game_manager.py       # Multi-game coordinator singleton
├── routes/                    # API endpoints (all use Response | None = None for HTMX redirects)
│   ├── game.py               # Create/join game
│   ├── lobby.py              # Lobby management and game start
│   ├── gameplay.py           # Voting, word guessing, game logic
│   └── websocket.py          # WebSocket handler for real-time updates
├── models/                    # Pydantic models
│   ├── requests.py           # Request DTOs
│   └── responses.py          # Response DTOs
├── services/                  # Business logic helpers
│   ├── voting.py             # Vote validation and tallying
│   ├── win_conditions.py     # Win detection logic
│   └── game_state.py         # State transition helpers
├── static/                    # Frontend assets
│   ├── css/custom.css
│   ├── js/websocket-client.js
│   └── js/htmx-config.js
├── templates/                 # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html            # Landing page
│   ├── join.html             # Join page
│   ├── lobby.html            # Game lobby
│   ├── game.html             # Active game
│   └── results.html          # Game over
└── tests/                     # Test suite (31 tests)
    ├── conftest.py           # Pytest fixtures
    └── services/             # Service tests
        ├── test_voting.py
        ├── test_win_conditions.py
        └── test_game_state.py
```

## Key Concepts

### Game Roles

1. **Villagers**: Know the secret word, must identify the Dragon
2. **Knights**: Know a similar (but different) word, think they are villagers, must identify the Dragon
3. **Dragon**: Doesn't know any word, must blend in to survive or guess the word if eliminated

### Role Distribution

| Players | Dragon | Knights | Villagers |
|---------|--------|---------|-----------|
| 3-4     | 1      | 0       | 2-3       |
| 5-6     | 1      | 1       | 3-4       |
| 7-8     | 1      | 2       | 4-5       |
| 9-10    | 1      | 3       | 5-6       |
| 11-12   | 1      | 4       | 6-7       |

### Game State Machine

```
LOBBY → (host starts) → PLAYING → (host initiates voting) → VOTING
  ↓                                                            ↓
  ↓ (players vote)                                             ↓
  ↓                                                            ↓
  → DRAGON_GUESS (if dragon eliminated) → FINISHED
  → FINISHED (if dragon survives with ≤2 players)
  → PLAYING (if game continues)
```

### Win Conditions

- **Villagers/Knights win**: Dragon is eliminated AND fails to guess the word
- **Dragon wins**:
  - Survives until ≤2 players remain, OR
  - Gets eliminated but correctly guesses the villager word

## Development Workflow

### Setup

```bash
cd app
uv sync --group dev  # Install all dependencies including dev tools
```

### Running the Server

```bash
cd app
uv run fastapi dev app.py    # Development mode (hot reload)
uv run fastapi run app.py    # Production mode
```

### Testing

```bash
cd app
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest -v -s        # Verbose with print statements
```

### Code Quality

```bash
cd app
uv run ruff format .       # Format code
uv run ruff check .        # Check for issues
uv run ruff check --fix .  # Auto-fix issues
uv run ty check .          # Type checking
```

### Pre-commit Checklist

Before committing, always run:
```bash
cd app
uv run ruff format .
uv run ruff check --fix .
uv run pytest
uv run ty check .
```

All commands should pass with no errors.

## Important Patterns

### 1. Response Parameter Pattern

All HTMX endpoints use `Response | None = None` for redirect headers:

```python
async def endpoint(response: Response | None = None):
    # ... logic ...
    if response:
        response.headers["HX-Redirect"] = f"/game/{game_id}/page"
    return {"status": "success"}
```

### 2. Exception Handling

Always use proper exception chaining:

```python
try:
    game.some_operation()
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
```

### 3. WebSocket Broadcasting

Game state updates are broadcast via WebSocket:

```python
await game.broadcast_state()
```

Each player receives a personalized state based on their role.

### 4. Game Session Access

Always retrieve games through the singleton:

```python
from core.game_manager import game_manager

game = game_manager.get_game(game_id)
if not game:
    raise HTTPException(status_code=404, detail="Game not found")
```

### 5. Type Safety

- Use `str | None` instead of `Optional[str]` (modern Python 3.10+ syntax)
- Use `strict=True` with `zip()` for safety
- Add null checks before accessing potentially None values

## Common Tasks

### Adding a New Word Pair

Edit `app/core/constants.py`:

```python
WORD_PAIRS = [
    ("elephant", "mammoth"),  # (villager_word, knight_word)
    # Add new pairs here
]
```

### Adding a New Test

1. Create test file in `tests/services/`
2. Import fixtures from `conftest.py`
3. Use class-based organization: `class TestFeatureName:`
4. Name test methods: `test_description_of_behavior`

Example:
```python
class TestMyFeature:
    def test_feature_works(self, started_game):
        # Arrange
        player = list(started_game.players.values())[0]

        # Act
        result = my_feature(started_game, player.id)

        # Assert
        assert result is True
```

### Adding a New Route

1. Create endpoint in appropriate router file (`routes/`)
2. Use proper type annotations
3. Add null checks for `Response` if using HTMX redirects
4. Handle exceptions with proper chaining
5. Broadcast state updates if game state changes

## Configuration Files

### pyproject.toml

Contains:
- Project metadata and dependencies
- Dev dependency group (pytest, ruff, ty)
- pytest configuration (testpaths, asyncio settings)
- ruff configuration (line-length=100, lint rules, format settings)

Key ruff lint rules:
- `E`, `W`: pycodestyle errors and warnings
- `F`: pyflakes
- `I`: isort (import sorting)
- `B`: flake8-bugbear (common bugs)
- `C4`: flake8-comprehensions
- `UP`: pyupgrade (modern Python syntax)
- `ASYNC`: async best practices (proper cleanup, unclosed clients)

## Testing Strategy

### Test Fixtures (conftest.py)

- `game_session`: Empty game session
- `game_with_players`: Game with 5 players in lobby
- `started_game`: Game that has started (roles assigned)
- `voting_game`: Game in voting state
- `sample_player`: Single player instance

### Test Organization

- Tests are organized by service/module
- Each test class focuses on one function or feature
- Tests follow Arrange-Act-Assert pattern
- All async code is automatically handled by pytest-asyncio

## Code Conventions

1. **Docstrings**: All functions have docstrings with Args and Returns
2. **Type Hints**: All parameters and return types are annotated
3. **Line Length**: Maximum 100 characters (enforced by ruff)
4. **Imports**: Auto-sorted by ruff (stdlib, third-party, local)
5. **String Quotes**: Double quotes (enforced by ruff)
6. **Indentation**: 4 spaces (no tabs)

## Common Pitfalls

1. **Don't forget to broadcast state**: After game state changes, always call `await game.broadcast_state()`
2. **Check game state**: Validate game is in correct state before operations
3. **Validate player permissions**: Check if player is host, alive, etc.
4. **Null checks**: Always check if `game.villager_word`, `game.knight_word` exist before using
5. **Type ignore comments**: Only use for known limitations (e.g., CORSMiddleware typing)

## Deployment

### Docker

```bash
docker build -t dragonseeker .
docker run -p 8000:8000 dragonseeker
```

### Digital Ocean App Platform

- Auto-deploys on push to `main` branch
- Configuration in `.do/app.yaml`
- Uses Dockerfile for build

## Useful Commands

```bash
# Find all TODO comments
grep -r "TODO" app/

# Check test coverage
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/services/test_voting.py -v

# Run specific test
uv run pytest tests/services/test_voting.py::TestCanVote::test_can_vote_in_voting_phase -v

# Format a single file
uv run ruff format app/routes/game.py

# Check a single file
uv run ruff check app/routes/game.py
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [HTMX Documentation](https://htmx.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [uv Documentation](https://docs.astral.sh/uv/)

## Notes for AI Assistants

- Always run tests after making changes
- Use the existing fixtures in `conftest.py` for tests
- Follow the type annotation patterns established in the codebase
- Check that all tools pass before considering work complete
- When adding features, update tests to maintain coverage
- Preserve HTMX patterns for frontend interactivity
- Remember that WebSocket updates are crucial for real-time gameplay

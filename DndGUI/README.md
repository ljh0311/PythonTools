# D&D Tools Collection

A comprehensive collection of Python-based tools for Dungeons & Dragons players and Dungeon Masters.

## Features

### 🎲 Dice Roller

- Quick dice buttons for common dice (d4, d6, d8, d10, d12, d20, d100)
- Custom dice expressions (e.g., "2d6+3", "1d20-2")
- Detailed roll history with individual dice results
- Support for modifiers and multiple dice

### 📚 Spell Database

- Searchable spell database with common D&D spells
- Detailed spell information including:
  - Spell level and school
  - Casting time and range
  - Components and duration
  - Full spell descriptions
- Real-time search functionality

### ⚔️ Initiative Tracker

- Add combatants with names, initiative, and HP
- Automatic initiative sorting (highest first)
- Turn tracking with visual indicators
- Easy next turn progression
- Clear combat management

### 🐉 Monster Manual

- Quick reference for common D&D monsters
- Monster statistics including:
  - Challenge rating and type
  - Armor class and hit points
  - Ability scores
  - Actions and descriptions
- Searchable monster database

### 📝 Campaign Notes

- Simple note-taking system for campaign information
- Create, edit, and delete notes
- Persistent storage in JSON format
- Perfect for session notes, NPC details, and world building

## Installation

1. Make sure you have Python 3.6+ installed
2. The tools use only standard library modules (tkinter, json, os, random, re)
3. No additional dependencies required

## Usage

### Running the Tools

1. **Main Launcher**: Run `python run_dnd_tools.py` to open the main launcher
2. **Individual Tools**: You can also run individual tools directly:
   - `python tools/dice_roller.py`
   - `python tools/spell_database.py`
   - `python tools/initiative_tracker.py`
   - `python tools/monster_manual.py`
   - `python tools/campaign_notes.py`

### File Storage

The tools automatically save data to JSON files in the same directory:

- `characters.json` - Character sheet data
- `campaign_notes.json` - Campaign notes

## Tool Details

### Dice Roller

- Click dice buttons for quick rolls
- Enter custom expressions like "3d6+2" for complex rolls
- View detailed results showing individual dice and modifiers
- Clear results to start fresh

### Spell Database

- Type in the search box to filter spells
- Click on any spell to view full details
- Currently includes sample spells (Fireball, Magic Missile, Cure Wounds)
- Easy to expand with more spells

### Initiative Tracker

- Add combatants with their initiative scores
- Click "Roll Initiative" to sort by initiative
- Use "Next Turn" to advance through combat
- Current turn is highlighted in the list

### Monster Manual

- Search monsters by name
- View complete monster statistics
- Currently includes sample monsters (Goblin, Orc, Red Dragon)
- Easy to expand with more monsters

### Campaign Notes

- Create new notes with titles and content
- Select notes from the list to edit
- Save all notes with the "Save All" button
- Notes persist between sessions

## Customization

### Adding More Spells

Edit `tools/spell_database.py` and add to the `self.spells` dictionary:

```python
"Spell Name": {
    "level": 1,
    "school": "Evocation",
    "casting_time": "1 action",
    "range": "60 feet",
    "components": "V, S",
    "duration": "Instantaneous",
    "description": "Spell description here..."
}
```

### Adding More Monsters

Edit `tools/monster_manual.py` and add to the `self.monsters` dictionary:

```python
"Monster Name": {
    "cr": "1/2",
    "type": "Humanoid",
    "size": "Medium",
    "ac": 13,
    "hp": "15 (2d8 + 6)",
    "speed": "30 ft.",
    "str": 16, "dex": 12, "con": 16, "int": 7, "wis": 11, "cha": 10,
    "actions": ["Action 1", "Action 2"],
    "description": "Monster description here..."
}
```

## Tips for D&D Players

1. **Dice Roller**: Perfect for quick combat rolls and skill checks
2. **Spell Database**: Great for spellcasters to quickly look up spell details
3. **Initiative Tracker**: Essential for DMs to manage combat encounters
4. **Monster Manual**: Quick reference during encounters
5. **Campaign Notes**: Keep track of important story elements and NPCs

## Future Enhancements

Potential additions to the tool collection:

- Character sheet with more detailed stats
- Equipment and inventory tracker
- Experience and leveling calculator
- Random encounter generator
- Weather and time tracker
- Party management tools

## Requirements

- Python 3.6 or higher
- tkinter (usually included with Python)
- Windows, macOS, or Linux

## License

This project is open source and available under the MIT License.

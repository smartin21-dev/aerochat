# AeroChat Commands Documentation

## User Commands

### Chat Commands
- `/votekick <username>` - Initiate a votekick against a user
  - Requires 3 votes to kick
  - Cannot votekick yourself
  - Cannot vote multiple times
  - Example: `/votekick BraveTiger123`

- `/voteskip` - Vote to skip the current video
  - Requires 30% of current users to vote (minimum 2 votes)
  - Can only vote once per video
  - Shows progress of votes in chat
  - Example: `/voteskip`

## Admin Commands

### Console Commands
These commands are executed in the server console using the Flask CLI.

- `flask forceskip` - Force skip the current video
  - Immediately skips to next video in queue
  - Broadcasts admin message to all users
  - Resets all voteskip votes
  - Example: `flask forceskip`

## Command Behavior

### Votekick System
1. User initiates votekick with `/votekick <username>`
2. Other users can vote by using the same command
3. When 3 votes are reached:
   - Target user is disconnected
   - System broadcasts kick message
   - User list is updated

### Voteskip System
1. User initiates voteskip with `/voteskip`
2. System shows current vote count and required votes
3. When threshold is reached (30% of users or minimum 2):
   - Current video is skipped
   - Next video in queue starts playing
   - System broadcasts skip message
   - Votes are reset

### Forceskip System
1. Admin executes `flask forceskip` in server console
2. System immediately:
   - Skips current video
   - Plays next video in queue
   - Broadcasts admin message
   - Resets all voteskip votes

## Notes
- All commands are case-sensitive
- Commands must be typed exactly as shown
- System messages will provide feedback on command success/failure
- Commands can only be used when appropriate (e.g., can't voteskip when no video is playing)
- Admin commands require server console access 
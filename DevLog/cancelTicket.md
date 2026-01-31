# The "Auto-Promotion" Logic
You don't need to manually manage "WL1, WL2". You just need a Queue. When a cancellation happens, a "Gap" opens up (e.g., Seat 1A is free from Delhi to Kanpur).

### The Algorithm:

1. Cancel the user's booking. This frees up Seat X for sequence A to B.

1. Fetch all WL tickets for that Train and Date, ordered by created_at ASC (First Come, First Served).

3. Loop through them:

    * Does the WL passenger's journey fit inside the gap A to B?

    * Yes? Assign Seat X to them. Promotion Done! Stop looking.

    * No? Check the next WL passenger.
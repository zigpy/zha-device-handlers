"""Module for EnOcean quirks implementations."""

# The switch modules have two rockers, A and B, each with a top (0) and a bottom (1)
# contact. The PTM 216Z reports these bits directly, the PTM 215Z sends a command per
# contact instead.
CONTACT_A0 = 0b0001
CONTACT_A1 = 0b0010
CONTACT_B0 = 0b0100
CONTACT_B1 = 0b1000

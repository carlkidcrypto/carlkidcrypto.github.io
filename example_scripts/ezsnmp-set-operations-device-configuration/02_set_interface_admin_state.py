#!/usr/bin/env python3
"""Example script for: SNMP Set Operations & Device Configuration with ezsnmp
Source: https://carlkidcrypto.github.io/blog/ezsnmp-set-operations-device-configuration.html
"""

def set_interface_admin_state(session: Session, if_index: int, state: str):
    """Set administrative status on a specific network interface."""
    state_map = {"up": 1, "down": 2, "testing": 3}
    if state not in state_map:
        raise ValueError(
            f"Invalid state '{state}'. Choose up/down/testing."
        )

    target_oid = f"ifAdminStatus.{if_index}"
    int_value = state_map[state]

    # Explicitly pass string representation of integer with 'i' type flag
    session.set([target_oid, 'i', str(int_value)])
    print(
        f"Interface index {if_index} set to {state.upper()} ({int_value})."
    )

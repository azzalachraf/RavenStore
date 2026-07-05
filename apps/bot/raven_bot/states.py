from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_query = State()


class CheckoutStates(StatesGroup):
    waiting_payment_id = State()


class SupportStates(StatesGroup):
    waiting_subject = State()
    waiting_message = State()


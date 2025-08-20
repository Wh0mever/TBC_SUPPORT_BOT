from aiogram.fsm.state import State, StatesGroup

class UserRegistration(StatesGroup):
    waiting_for_contact = State()

class TicketResponse(StatesGroup):
    waiting_for_response = State()
    waiting_for_ticket_id = State()

class AdminManagement(StatesGroup):
    waiting_for_admin_id = State()

"""Customer screen: My Table Bookings (page name: "bookings")."""
from dashboard import CustomerPage
from check_availability import BOOKING_COLUMNS, DataTable, booking_rows, sync_state


class MyBookingsPage(CustomerPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, active="reservation")
        self.table = DataTable(self.content, BOOKING_COLUMNS,
                               empty_text="You have no table bookings yet.")
        self.table.pack(fill="both", expand=True, pady=(10, 0))

    def refresh(self):
        self.set_header("My Table Bookings", "Your table reservations.")
        sync_state(self.controller)
        self.table.set_rows(booking_rows(self.controller.state["reservations"]))
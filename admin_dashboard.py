"""Admin Dashboard placeholder."""
from admin_reservation import AdminPage


class AdminDashboardPage(AdminPage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller, active="admin_dashboard")

    def refresh(self):
        self.set_header("Dashboard", "Admin overview coming soon.")


if __name__ == "__main__":
    import main
    main.App("admin_dashboard").mainloop()
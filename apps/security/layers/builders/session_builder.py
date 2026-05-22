class SessionBuilder:
    def __init__(self, user, request):
        self.user = user
        self.request = request
        self.session_data = {}
        self.redirect_url = None

    def build_initials(self):
        person = getattr(self.user, "person", None)
        self.session_data["initials"] = getattr(person, "initials", "NN") if person else "US"
        return self

    def build_session_name(self):
        person = getattr(self.user, "person", None)
        self.session_data["session_name"] = getattr(person, "short_name", self.user.username)
        return self

    def build_group_name(self):
        group = self.user.groups.first()
        self.session_data["group"] = group.name
        return self

    def check_forced_password(self):
        if getattr(self.user, "force_password", False):
            self.redirect_url = "security:users:password_change"
        return self

    def build(self):
        for key, value in self.session_data.items():
            self.request.session[key] = value
        return self.redirect_url

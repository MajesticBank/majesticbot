"""This file defines the Command( class which stores the name of the command, its callback, docs the acceptable
parameter counts and aliases """

from MajesticBank import Style


class Command:
    def __init__(self, command_name: str, callback, docs: dict = {}, parameter_counts: list = None,
                 aliases: list = None):
        self.command_name = command_name
        self.callback = callback
        self.docs = docs
        self.parameter_counts = parameter_counts
        self.aliases = aliases

    def get_command_help(self) -> str:
        """

        :return: A HTML-formatted string containing all the docs info
        """
        txt = ""
        txt += "/" + self.command_name + "\n"

        if "description" in self.docs:
            txt += Style.i(self.docs["description"]) + "\n"
        if "usage" in self.docs:
            txt += Style.b("Usage:") + " /" + self.command_name + Style.code(self.docs["usage"]) + "\n"

        if "examples" in self.docs:
            if isinstance(self.docs["examples"], list):
                for example in self.docs["examples"]:
                    txt += Style.b("Example:") + " /" + self.command_name + " " + Style.code(example) + "\n"
            elif isinstance(self.docs["examples"], str):
                txt += Style.b("Example:") + " /" + self.command_name + " " + Style.code(self.docs["examples"]) + "\n"

        txt += "\n"
        return txt

    def name_and_aliases(self):
        """

        :return: A list of all the names this command can be triggered with
        """
        if not self.aliases:
            return [self.command_name]
        return [self.command_name, *self.aliases]

    def name_and_aliases_regex(self):
        return "|".join(self.name_and_aliases())

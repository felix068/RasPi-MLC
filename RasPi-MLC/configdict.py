import json
import os
from typing import Any, Hashable, Optional

force_attr = ("reload", "save")


def should_force_attr(obj: 'ConfigDict', attr: str):
	return attr.startswith("_") or attr in dir(obj)


def set_recursive_default(dic: dict, key: Optional[Hashable], default: Any = None) -> None:
	if key is None:
		subdic = dic
	else:
		dic.setdefault(key, default)
		subdic = dic[key]
	if isinstance(default, dict):
		for subkey, subval in default.items():
			set_recursive_default(subdic, subkey, subval)


class ConfigDict(dict):
	def __init__(self, configfile, defaults=None):
		super().__init__()
		self._configfile = configfile
		if defaults is None:
			defaults = {}
		self._defaults = defaults
		self.reload()

	def reload(self):
		self.clear()
		if os.path.exists(self._configfile):
			with open(self._configfile, 'r', encoding="utf8") as f:
				self.update(json.load(f))

		set_recursive_default(self, None, self._defaults)
		self.save()

	def save(self, **kwargs):
		kwargs.setdefault("indent", 2)
		with open(self._configfile, 'w', encoding="utf8") as f:
			json.dump(self, f, **kwargs)

	def __setattr__(self, key, value):
		if should_force_attr(self, key):
			super().__setattr__(key, value)
		else:
			self.__setitem__(key, value)

	def __delattr__(self, key):
		if should_force_attr(self, key):
			super().__delattr__(key)
		else:
			self.__delitem__(key)

	def __getattribute__(self, key):
		if should_force_attr(self, key):
			return super().__getattribute__(key)
		else:
			return self.__getitem__(key)

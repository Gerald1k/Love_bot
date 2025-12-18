from dataclasses import dataclass
from typing import Optional
from bson import ObjectId


@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    partner_username: Optional[str] = None
    partner_id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            telegram_id=data["telegram_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            partner_username=data.get("partner_username"),
            partner_id=data.get("partner_id")
        )
    
    def to_dict(self) -> dict:
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "partner_username": self.partner_username,
            "partner_id": self.partner_id
        }


@dataclass
class Gift:
    user_id: ObjectId
    name: str
    price: Optional[str] = None
    link: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Gift":
        return cls(
            user_id=data["user_id"],
            name=data["name"],
            price=data.get("price"),
            link=data.get("link"),
            description=data.get("description")
        )
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "price": self.price,
            "link": self.link,
            "description": self.description
        }

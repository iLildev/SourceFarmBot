from typing import TypedDict


class Source(TypedDict):
    id: int
    name: str
    category: str
    points: int
    installs: int
    rating: float
    description: str
    author: str
    version: str


FAKE_SOURCES: list[Source] = [
    {
        "id": 1,
        "name": "ChatFlow Pro",
        "category": "🤖 Chatbot",
        "points": 250,
        "installs": 1420,
        "rating": 4.8,
        "description": "بوت محادثة احترافي مع ردود تلقائية ذكية",
        "author": "DevCore",
        "version": "2.1.0",
    },
    {
        "id": 2,
        "name": "ShopBot X",
        "category": "🛒 E-Commerce",
        "points": 500,
        "installs": 3210,
        "rating": 4.6,
        "description": "متجر إلكتروني كامل داخل تيليجرام",
        "author": "MarketLabs",
        "version": "3.0.1",
    },
    {
        "id": 3,
        "name": "AdminPanel Lite",
        "category": "⚙️ Admin",
        "points": 150,
        "installs": 890,
        "rating": 4.3,
        "description": "لوحة تحكم إدارية بسيطة لإدارة المستخدمين",
        "author": "ToolKit",
        "version": "1.4.2",
    },
    {
        "id": 4,
        "name": "NewsBot Daily",
        "category": "📰 Content",
        "points": 100,
        "installs": 5600,
        "rating": 4.9,
        "description": "جدولة ونشر المحتوى تلقائياً",
        "author": "ContentFlow",
        "version": "1.2.0",
    },
    {
        "id": 5,
        "name": "SupportDesk AI",
        "category": "💬 Support",
        "points": 350,
        "installs": 2100,
        "rating": 4.7,
        "description": "نظام دعم عملاء متكامل مع تذاكر",
        "author": "HelpSys",
        "version": "2.0.0",
    },
    {
        "id": 6,
        "name": "CryptoTracker",
        "category": "📈 Finance",
        "points": 200,
        "installs": 7800,
        "rating": 4.5,
        "description": "تتبع أسعار العملات الرقمية لحظة بلحظة",
        "author": "FinBot",
        "version": "1.8.3",
    },
]

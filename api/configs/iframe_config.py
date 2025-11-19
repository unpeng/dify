from pydantic import Field
from pydantic_settings import BaseSettings


class IframeConfig(BaseSettings):
    """
    Configuration for iframe integration
    """

    # 是否允许iframe嵌入
    ALLOW_EMBED: bool = Field(
        description="Allow embedding in iframe",
        default=False,
    )

    # 允许嵌入的域名列表（逗号分隔）
    IFRAME_ALLOWED_ORIGINS: str = Field(
        description="Comma-separated list of allowed origins for iframe embedding",
        default="*",
    )

    # iframe认证token的有效期（分钟）
    IFRAME_AUTH_TOKEN_EXPIRE_MINUTES: int = Field(
        description="Iframe authentication token expiration time in minutes",
        default=60,
    )

    # 外部系统的token验证URL
    EXTERNAL_TOKEN_VERIFY_URL: str = Field(
        description="External system token verification URL",
        default="",
    )

    # 外部系统的用户信息获取URL
    EXTERNAL_USER_INFO_URL: str = Field(
        description="External system user info URL",
        default="",
    )

    # 外部系统的API密钥
    EXTERNAL_SYSTEM_API_KEY: str = Field(
        description="External system API key for token verification",
        default="",
    )

    # 是否启用iframe通信日志
    IFRAME_COMMUNICATION_LOG_ENABLED: bool = Field(
        description="Enable iframe communication logging",
        default=False,
    )

    # iframe会话超时时间（分钟）
    IFRAME_SESSION_TIMEOUT_MINUTES: int = Field(
        description="Iframe session timeout in minutes",
        default=480,  # 8小时
    )

    # 是否自动创建不存在的用户
    IFRAME_AUTO_CREATE_USER: bool = Field(
        description="Automatically create user if not exists",
        default=True,
    )

    # 默认用户角色
    IFRAME_DEFAULT_USER_ROLE: str = Field(
        description="Default role for iframe users",
        default="admin",
    )

    # 默认界面语言
    IFRAME_DEFAULT_LANGUAGE: str = Field(
        description="Default interface language for iframe users",
        default="zh-Hans",
    )

    def get_allowed_origins(self) -> list[str]:
        """Get list of allowed origins"""
        if self.IFRAME_ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.IFRAME_ALLOWED_ORIGINS.split(",") if origin.strip()]

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        allowed_origins = self.get_allowed_origins()
        return "*" in allowed_origins or origin in allowed_origins

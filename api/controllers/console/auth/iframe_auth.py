import logging
from typing import Any, Optional

import requests
from flask import make_response, request
from flask_restx import Resource, reqparse
from werkzeug.exceptions import Unauthorized

from configs import dify_config
from controllers.console import console_ns
from controllers.console.wraps import setup_required
from events.tenant_event import tenant_was_created
from extensions.ext_database import db
from libs.helper import extract_remote_ip
from libs.token import (
    set_access_token_to_cookie,
    set_csrf_token_to_cookie,
    set_refresh_token_to_cookie,
)
from models.account import Account, Tenant, TenantAccountJoin, TenantStatus
from services.account_service import AccountService, TenantService

logger = logging.getLogger(__name__)


@console_ns.route("/iframe-auth")
class IframeAuthApi(Resource):
    """Resource for iframe authentication."""

    @setup_required
    def post(self):
        """Authenticate user for iframe integration."""
        parser = (
            reqparse.RequestParser()
            .add_argument("token", type=str, required=True, location="json")
            .add_argument("tenant", type=str, required=False, location="json")
        )
        args = parser.parse_args()

        logger.info("request: %s", request.headers.get("Origin"))

        # 根据token获取用户信息
        user_info = self._get_user_from_token(args["token"])
        if not user_info:
            raise Unauthorized("Unable to get user information")

        # 获取或创建用户账户
        account = self._get_or_create_account(user_info, args["tenant"])

        # 确保用户有工作空间
        tenants = self._get_join_tenants_by_name(account, args["tenant"])

        if not tenants:
            raise Unauthorized("User has no workspace named %s", args["tenant"])

        # 获取用户角色
        role = TenantService.get_user_role(account, tenants[0])

        # 生成登录token
        token_pair = AccountService.login(account=account, ip_address=extract_remote_ip(request))

        # 创建响应并设置cookie
        response = make_response({
            "result": "success",
            "user": {
                 "id": account.id,
                 "name": account.name,
                 "email": account.email,
                 "role": role or None}
            })

        # 设置SameSite=None以支持iframe跨域
        set_access_token_to_cookie(request, response, token_pair.access_token)
        set_refresh_token_to_cookie(request, response, token_pair.refresh_token)
        set_csrf_token_to_cookie(request, response, token_pair.csrf_token)

        return response

    def _get_user_from_token(self, token: str) -> Optional[dict[str, Any]]:
        """
        从token中获取用户信息
        调用外部系统的API获取用户信息
        """
        try:
            if not dify_config.EXTERNAL_USER_INFO_URL:
                logger.error("External user info URL is not configured")
                return None

            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                dify_config.EXTERNAL_USER_INFO_URL,
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error("Failed to fetch user info with status code: %s", response.status_code)
                return None

            user_data = response.json()
            logger.info("Fetched user info: %s", user_data)
            return {
                "email": user_data.get('email'),
                "name": user_data.get('name')
            }
        except Exception as e:
            logger.exception("Error fetching user info: %s", str(e))
            return None

    def _get_or_create_account(self, user_info: dict[str, Any], tenant_name: Optional[str] = None) -> Account:
        """获取或创建用户账户"""
        email = user_info.get("email")
        name = user_info.get("name")

        if not email:
            raise ValueError("Email is required for account creation")

        # 尝试通过邮箱获取现有账户
        try:
            account = AccountService.get_user_through_email(email)
            if account:
                tenants = self._get_join_tenants_by_name(account, tenant_name)
                if not tenants:
                    tenant = db.session.query(Tenant).filter_by(name=tenant_name).first()
                    if not tenant:
                        logger.info("create_owner_tenant_if_not_exist: %s", tenant_name)
                        # TenantService.create_owner_tenant_if_not_exist(account=account, name=tenant_name)
                        self._create_owner_tenant_if_not_exist(account=account, name=tenant_name)
                    else:
                        logger.info("create_tenant_member: %s", tenant_name)
                        TenantService.create_tenant_member(tenant=tenant,
                                                           account=account,
                                                           role=dify_config.IFRAME_DEFAULT_USER_ROLE)

                new_tenant = db.session.query(Tenant).filter_by(name=tenant_name).first()
                if new_tenant is None:
                    raise ValueError("Tenant not found")
                TenantService.switch_tenant(account, new_tenant.id)
                logger.info("account[%s]: %s", new_tenant.id, account)
                return account
        except Exception as e:
            logger.exception("Error fetching account info: %s", str(e))
            pass

        logger.info("Creating account with email: %s, name: %s", email, name)
        # 如果账户不存在，创建新账户
        try:
            account = self._create_account_and_tenant(
                email=email,
                name=name,
                interface_language="zh-Hans",
                tenant_name=tenant_name,
            )
            return account
        except Exception as e:
            logger.exception("Failed to create account: %s", e)
            # 如果创建失败，尝试再次获取（可能是并发创建）
            try:
                return AccountService.get_user_through_email(email)
            except Exception as inner_e:
                logger.exception("Failed to retrieve account after creation attempt: %s", inner_e)
                raise e

    def _create_account_and_tenant(self,
                                   email: str,
                                   name: str,
                                   interface_language: str,
                                   tenant_name: Optional[str] = None) -> Account:
        """create account"""
        account = AccountService.create_account(
            email=email, name=name, interface_language=interface_language, password=None
        )

        if not tenant_name:
            tenant_name = f"{name}'s Workspace"

        tenant = db.session.query(Tenant).filter_by(name=tenant_name).first()

        if not tenant:
            TenantService.create_owner_tenant_if_not_exist(account=account, name=tenant_name)
        else:
            TenantService.create_tenant_member(tenant=tenant,
                                               account=account,
                                               role=dify_config.IFRAME_DEFAULT_USER_ROLE)

        return account

    def _get_join_tenants_by_name(self, account: Account, tenant_name: str) -> list[Tenant]:
        """Get account join tenants by name"""
        return (
            db.session.query(Tenant)
            .join(TenantAccountJoin, Tenant.id == TenantAccountJoin.tenant_id)
            .where(TenantAccountJoin.account_id == account.id,
                   Tenant.status == TenantStatus.NORMAL,
                   Tenant.name == tenant_name)
            .all()
        )

    def _create_owner_tenant_if_not_exist(self,
                                          account: Account, name: str | None = None, is_setup: bool | None = False):
        """Create owner tenant if not exist"""

        if name:
            tenant = TenantService.create_tenant(name=name, is_setup=is_setup)
        else:
            tenant = TenantService.create_tenant(name=f"{account.name}'s Workspace", is_setup=is_setup)

        TenantService.create_tenant_member(tenant, account, role="owner")
        account.current_tenant = tenant
        db.session.commit()
        tenant_was_created.send(tenant)

import asyncio
from pyracing.constants import Category
from ..helpers import *
from ..errors.name_not_found import NameNotFound


class UpdateUser:
    def __init__(self, pyracing, log):
        self.pyracing = pyracing
        self.log = log

    async def update_user_in_dict(self, user_id, guild_dict):
        """This updates a user inside the dict without saving to any files"""
        self.log.info(f'Updating user: {user_id}')
        iracing_id = guild_dict[user_id]['iracing_id']

        try:
            await self.update_driver_name(user_id, guild_dict, iracing_id)
        except Exception as e:
            self.handle_exceptions(self.update_driver_name.__name__, e)

        try:
            await self.update_career_stats(user_id, guild_dict, iracing_id)
        except Exception as e:
            self.handle_exceptions(self.update_career_stats.__name__, e)

        try:
            await self.update_yearly_stats(user_id, guild_dict, iracing_id)
        except Exception as e:
            self.handle_exceptions(self.update_yearly_stats.__name__, e)

        try:
            await self.update_iratings(user_id, guild_dict, iracing_id, Category.oval)
        except Exception as e:
            self.handle_exceptions(self.update_iratings.__name__, e)

        try:
            await self.update_iratings(user_id, guild_dict, iracing_id, Category.road)
        except Exception as e:
            self.handle_exceptions(self.update_iratings.__name__, e)

        try:
            await self.update_iratings(user_id, guild_dict, iracing_id, Category.dirt_road)
        except Exception as e:
            self.handle_exceptions(self.update_iratings.__name__, e)

        try:
            await self.update_iratings(user_id, guild_dict, iracing_id, Category.dirt_oval)
        except Exception as e:
            self.handle_exceptions(self.update_iratings.__name__, e)

        try:
            await self.update_license_class(user_id, guild_dict, iracing_id, Category.oval)
        except Exception as e:
            self.handle_exceptions(self.update_license_class.__name__, e)

        try:
            await self.update_license_class(user_id, guild_dict, iracing_id, Category.road)
        except Exception as e:
            self.handle_exceptions(self.update_license_class.__name__, e)

        try:
            await self.update_license_class(user_id, guild_dict, iracing_id, Category.dirt_road)
        except Exception as e:
            self.handle_exceptions(self.update_license_class.__name__, e)

        try:
            await self.update_license_class(user_id, guild_dict, iracing_id, Category.dirt_oval)
        except Exception as e:
            self.handle_exceptions(self.update_license_class.__name__, e)

        self.log.info(f'Finished updating user: {user_id}')
        return guild_dict

    async def update_driver_name(self, user_id, guild_dict, cust_id):
        try:
            response = await self.pyracing.driver_status(cust_id=cust_id)
            name = parse_encoded_string(response.name)
            guild_dict[user_id]['name'] = name
            return name
        except:
            self.log.warning(f'Name not found for {cust_id}')
            raise NameNotFound

    async def update_career_stats(self, user_id, guild_dict, iracing_id):
        career_stats_list = await self.pyracing.career_stats(iracing_id)
        if career_stats_list:
            guild_dict[user_id]['career_stats'] = list(map(lambda x: x.__dict__, career_stats_list))
            return career_stats_list
        else:
            return []

    async def update_yearly_stats(self, user_id, guild_dict, iracing_id):
        yearly_stats_list = await self.pyracing.yearly_stats(iracing_id)
        if yearly_stats_list:
            guild_dict[user_id]['yearly_stats'] = list(map(lambda x: x.__dict__, yearly_stats_list))
            return yearly_stats_list
        else:
            return []

    async def update_iratings(self, user_id, guild_dict, iracing_id, category):
        chart_data = await self.pyracing.irating(iracing_id, category.value)
        if not chart_data.current():
            return []

        json_iratings = []
        for irating in chart_data.content:
            json_iratings.append([irating.datetime().strftime(datetime_format), irating.value])

        guild_dict[user_id][f'{category.name}_irating'] = json_iratings

        return json_iratings

    async def update_license_class(self, user_id, guild_dict, iracing_id, category):
        chart_data = await self.pyracing.license_class(iracing_id, category.value)
        if not chart_data.current():
            return 'N/A'

        license_class = str(chart_data.current().class_letter()) + ' ' + str(chart_data.current().safety_rating())
        guild_dict[user_id][f'{category.name}_license_class'] = license_class
        return license_class

    def handle_exceptions(self, method_name, e):
        self.log.warning(f'update failed in method {method_name}. Exception: {str(e)}')

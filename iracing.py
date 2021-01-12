from redbot.core import commands
import dotenv
from pyracing import client as pyracing
from .storage import *
import discord
from discord.ext import tasks
from datetime import datetime
import logging
from logdna import LogDNAHandler
from prettytable import PrettyTable, ALL
import imgkit
from .helpers import *
from .html_builder import *
from bokeh.plotting import figure, output_file, save
from bokeh.io import export_png
from bokeh.palettes import Category20
from bokeh.models import Legend
import itertools
from selenium import webdriver
from .commands.update import Update
import copy


options = webdriver.chrome.options.Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument("--headless")
options.add_argument("--hide-scrollbars")

dotenv.load_dotenv()

logdna_key = os.getenv("LOGDNA_INGESTION_KEY")
log = logging.getLogger('logdna')
log.setLevel(logging.DEBUG)
handler = LogDNAHandler(logdna_key, {'hostname': os.getenv("LOG_LOCATION")})
log.addHandler(handler)


class Iracing(commands.Cog):
    """A cog that can give iRacing data about users"""

    def __init__(self):
        super().__init__()
        self.pyracing = pyracing.Client(
            os.getenv("IRACING_USERNAME"),
            os.getenv("IRACING_PASSWORD")
        )
        self.all_series = []
        self.updater = Update(self.pyracing, log)
        self.update_all_servers.start()

    @tasks.loop(hours=1, reconnect=False)
    async def update_all_servers(self):
        """Update all users career stats and iratings for building a current leaderboard"""
        self.all_series = await self.pyracing.current_seasons(series_id=True)
        self.all_series.sort(key=lambda x: x.series_id)
        log.info('Successfully got all current season data')

        await self.updater.update_all_servers()

    @commands.command()
    async def update(self, ctx):
        """Update all users career and yearly stats and iratings for building a current leaderboard.
        This is run every hour anyways, so it isn't necessary most of the time to run manually"""
        await self.updater.update(ctx)

    @commands.command()
    async def recentraces(self, ctx, *, iracing_id=None):
        """Shows the recent race data for the given iracing id. If no iracing id is provided it will attempt
        to use the stored iracing id for the user who called the command."""
        async with ctx.typing():
            user_id = str(ctx.author.id)
            guild_id = str(ctx.guild.id)
            if not iracing_id:
                iracing_id = get_user_iracing_id(user_id, guild_id)
                if not iracing_id:
                    await ctx.send('Please send an iRacing ID with the command or link your own with `!saveid <iRacing '
                                   'ID>`')
                    return

            races_stats_list = await self.get_last_races(user_id, guild_id, iracing_id)

            if races_stats_list:
                table_html_string = recent_races_table_string(races_stats_list, iracing_id, self.all_series)
                filename = f'{guild_id}_{iracing_id}_recent_races.jpg'
                imgkit.from_string(table_html_string, filename)
                await ctx.send(file=discord.File(filename))
                cleanup_file(filename)
            else:
                await ctx.send('Recent races not found for user: ' + iracing_id)

    @commands.command()
    async def lastseries(self, ctx, *, iracing_id=None):
        """Shows the recent series data for the given iracing id. If no iracing id is provided it will attempt
        to use the stored iracing id for the user who called the command."""
        async with ctx.typing():
            user_id = str(ctx.author.id)
            guild_id = str(ctx.guild.id)
            if not iracing_id:
                iracing_id = get_user_iracing_id(user_id, guild_id)
                if not iracing_id:
                    await ctx.send('Please send an iRacing ID with the command or link your own with `!saveid <iRacing '
                                   'ID>`')
                    return

            last_series = await self.pyracing.last_series(iracing_id)

            if last_series:
                table_html_string = get_last_series_html_string(last_series, iracing_id)
                filename = f'{guild_id}_{iracing_id}_last_series.jpg'
                imgkit.from_string(table_html_string, filename)
                await ctx.send(file=discord.File(filename))
                cleanup_file(filename)
            else:
                await ctx.send('Recent races not found for user: ' + iracing_id)

    @commands.command()
    async def yearlystats(self, ctx, *, iracing_id=None):
        """Shows the yearly stats for the given iracing id. If no iracing id is provided it will attempt
        to use the stored iracing id for the user who called the command."""
        async with ctx.typing():
            user_id = str(ctx.author.id)
            guild_id = str(ctx.guild.id)
            if not iracing_id:
                iracing_id = get_user_iracing_id(user_id, guild_id)
                if not iracing_id:
                    await ctx.send('Please send an iRacing ID after the command or link your own with `!saveid <iRacing '
                                   'ID>`')
                    return

            guild_dict = get_guild_dict(guild_id)
            yearly_stats = await self.updater.update_user.update_yearly_stats(user_id, guild_dict, iracing_id)

            if yearly_stats:
                yearly_stats_html = get_yearly_stats_html(yearly_stats, iracing_id)
                filename = f'{iracing_id}_yearly_stats.jpg'
                imgkit.from_string(yearly_stats_html, filename)
                await ctx.send(file=discord.File(filename))
                cleanup_file(filename)
            else:
                await ctx.send('No yearly stats found for user: ' + str(iracing_id))

    @commands.command()
    async def careerstats(self, ctx, *, iracing_id=None):
        """Shows the career stats for the given iracing id. If no iracing id is provided it will attempt
        to use the stored iracing id for the user who called the command."""
        async with ctx.typing():
            user_id = str(ctx.author.id)
            guild_id = str(ctx.guild.id)
            if not iracing_id:
                iracing_id = get_user_iracing_id(user_id, guild_id)
                if not iracing_id:
                    await ctx.send('Please send an iRacing ID after the command or link your own with `!saveid <iRacing'
                                   ' ID>`')
                    return

            guild_dict = get_guild_dict(guild_id)
            career_stats = await self.updater.update_user.update_career_stats(user_id, guild_dict, iracing_id)

            if career_stats:
                career_stats_html = get_career_stats_html(career_stats, iracing_id)
                filename = f'{iracing_id}_career_stats.jpg'
                imgkit.from_string(career_stats_html, filename)
                await ctx.send(file=discord.File(filename))
                cleanup_file(filename)
            else:
                await ctx.send('No career stats found for user: ' + str(iracing_id))

    @commands.command()
    async def saveid(self, ctx, *, iracing_id):
        """Save your iRacing ID to be placed on the leaderboard.
        Your ID can be found by the top right of your account page under "Customer ID"."""

        if not iracing_id.isdigit():
            await ctx.send('Oops, this ID does not seem to be valid. '
                           + 'Make sure you only write the numbers and not any symbols with the ID.'
                           + 'Your ID can be found by the top right of your account page under "Customer ID".')
            return

        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)

        save_iracing_id(user_id, guild_id, iracing_id)
        await ctx.send('iRacing ID successfully saved. Use `!update` to see this user on the leaderboard.')

    @commands.command()
    async def leaderboard(self, ctx, category='road', type='career'):
        """Displays a leaderboard of the users who have used `!saveid`.
        If the data is not up to date, try `!update` first.
        The categories are `road`, `oval`, `dirtroad`, and `dirtoval` and
        the types are `career` and `yearly`. Default is `road` `career`"""
        delete_missing_users(ctx.guild)
        async with ctx.typing():
            if type not in ['career', 'yearly']:
                await ctx.send('Please try again with one of these types: `career`, `yearly`')
                return

            if category not in ['road', 'oval', 'dirtroad', 'dirtoval']:
                await ctx.send('Please try again with one of these categories: `road`, `oval`, `dirtroad`, `dirtoval`')
                return

            is_yearly = (type != 'career')

            guild_dict = get_guild_dict(ctx.guild.id)
            leaderboard_data = get_relevant_leaderboard_data(guild_dict, category)
            table_html_string = get_leaderboard_html_string(leaderboard_data, ctx.guild, category, log, is_yearly)
            filename = f'{ctx.guild.id}_leaderboard.jpg'
            imgkit.from_string(table_html_string, filename)
            await ctx.send(file=discord.File(filename))
            cleanup_file(filename)

    @commands.command()
    async def iratings(self, ctx, category='road'):
        async with ctx.typing():
            if category not in ['road', 'oval', 'dirtroad', 'dirtoval']:
                ctx.send('The category should be one of `road`, `oval`, `dirtroad`, `dirtoval`')
                return

            category_id = category_id_from_string(category)

            today = datetime.now()
            date_6mo_ago = datetime(today.year, today.month - 6, today.day)

            p = figure(
                title=f'{lowercase_to_readable_categories(category)} iRatings',
                x_axis_type='datetime',
                x_range=(date_6mo_ago, datetime.now())
            )
            p.toolbar.logo = None
            p.toolbar_location = None
            legend = Legend(location=(0, -10))
            p.add_layout(legend, 'right')
            output_file('output_iratings.html')

            colors = itertools.cycle(Category20[20])

            irating_dicts = await saved_users_irating_charts(ctx.guild.id, category_id)
            for irating_dict in irating_dicts:
                for user_id, iratings_list in irating_dict.items():
                    member = ctx.guild.get_member(int(user_id))
                    datetimes = []
                    iratings = []
                    for irating in iratings_list:
                        datetimes.append(irating[0])
                        iratings.append(irating[1])

                    p.line(
                        datetimes,
                        iratings,
                        legend_label=member.display_name,
                        line_width=2,
                        color=next(colors)
                    )

            export_png(p, filename=f'irating_graph_{ctx.guild.id}.png', webdriver=webdriver.Chrome(options=options))
            await ctx.send(file=discord.File(f'irating_graph_{ctx.guild.id}.png'))

    @commands.command()
    async def allseries(self, ctx):
        road, oval, dirt_road, dirt_oval = [], [], [], []
        for season in self.all_series:
            if season.cat_id == 2:
                road.append(season)
            if season.cat_id == 1:
                oval.append(season)
            if season.cat_id == 4:
                dirt_road.append(season)
            if season.cat_id == 3:
                dirt_oval.append(season)

        html_strings = [
            build_series_html_string(road, 'Road Series'),
            build_series_html_string(oval, 'Oval Series'),
            build_series_html_string(dirt_road, 'Dirt Road Series'),
            build_series_html_string(dirt_oval, 'Dirt Oval Series')
        ]

        for string in html_strings:
            filename = f'{ctx.guild.id}_series.jpg'
            imgkit.from_string(string, filename)
            await ctx.send(file=discord.File(filename))
            cleanup_file(filename)

    @commands.command()
    async def setfavseries(self, ctx, *, ids):
        """Use command `!allseries` to get a list of all series and ids.
            Then use this command `!setfavseries` with a list of comma
            separated ids to set your favorite series"""
        id_list = ids.replace(' ', '').split(',')
        id_list = [x for x in id_list if x]
        try:
            parsed_ids = list(map(int, id_list))
            if not ids_valid_series(self.all_series, parsed_ids):
                await ctx.send('Please enter a comma separated list of numbers which correspond to'
                               'series IDs from the `!allseries` command')
                return

            set_guild_favorites(ctx.guild.id, parsed_ids)
            await ctx.send(f'Successfully saved favorite series: {parsed_ids}')
        except ValueError:
            await ctx.send('Please enter a comma separated list of numbers which correspond to'
                           'series IDs from the `!allseries` command')

    @commands.command()
    async def addfavseries(self, ctx, series_id):
        try:
            series_id_int = int(series_id)
            if not ids_valid_series(self.all_series, [series_id_int]):
                await ctx.send('Series ID must be a number associated to a series in `!allseries`')
                return
            current_favorites = get_guild_favorites(ctx.guild.id)
            current_favorites.append(series_id_int)
            current_favorites.sort()
            set_guild_favorites(ctx.guild.id, current_favorites)
            await ctx.send(f'Successfully added series: {series_id}')
        except:
            await ctx.send('Series ID must be a number associated to a series in `!allseries`')

    @commands.command()
    async def removefavseries(self, ctx, series_id):
        try:
            series_id_int = int(series_id)
            current_favorites = get_guild_favorites(ctx.guild.id)
            if series_id_int not in current_favorites:
                await ctx.send('Series ID must be a current favorite series. '
                               'Your current favorites can be found with `!currentseries`')
                return
            current_favorites.remove(series_id_int)
            set_guild_favorites(ctx.guild.id, current_favorites)
            await ctx.send(f'Successfully removed series: {series_id}')
        except:
            await ctx.send('Series ID must be a current favorite series. '
                           'Your current favorites can be found with `!currentseries`')

    @commands.command()
    async def currentseries(self, ctx):
        favorites = get_guild_favorites(ctx.guild.id)
        if not favorites:
            await ctx.send('Follow the directions by calling `!setfavseries` to set favorite'
                           'series before ')
            return

        series = series_from_ids(favorites, self.all_series)
        if not series:
            await ctx.send('Series not found, wait a minute and try again or contact an admin.')

        race_week = series[0].race_week - 1  # This is 1 indexed for some reason, but the tracks aren't
        this_week_string = build_race_week_string(race_week, series, 'This Week', log)
        next_week_string = build_race_week_string(race_week+1, series, 'Next Week', log)

        this_week_filename = f'{ctx.guild.id}_this_week.jpg'
        next_week_filename = f'{ctx.guild.id}_next_week.jpg'
        imgkit.from_string(this_week_string, this_week_filename)
        imgkit.from_string(next_week_string, next_week_filename)
        await ctx.send(file=discord.File(this_week_filename))
        await ctx.send(file=discord.File(next_week_filename))
        cleanup_file(this_week_filename)
        cleanup_file(next_week_filename)

    async def get_last_races(self, user_id, guild_id, iracing_id):
        races_stats_list = await self.pyracing.last_races_stats(iracing_id)
        if races_stats_list:
            log.info('found a races stats list for user: ' + str(iracing_id))
            update_user(user_id, guild_id, None, None, copy.deepcopy(races_stats_list))
            return races_stats_list

# Shepherd

[![Python Version](https://img.shields.io/badge/Python-3.7-brightgreen.svg)](.) [![License](https://img.shields.io/badge/License-BSD3-darkred.svg)](.)

> **_NOTE:_**  This project has been archived! I started working on some ideas for domain management in 2018. In January 2019,
> I released Shepherd as a proof-of-concept web application for managing domains with a UI. Shepherd was a success, but
> it became clear there was so much more potential for red team management and reporting. I learned much about Django with
> this project, so I started fresh and rebuilt Shepherd as a sub-application of [Ghostwriter](https://github.com/GhostManager/Ghostwriter).
> The project lives on there!
> 
> If you are interested in the original Shepherd, it is still available here as an artifact. I will not be updating it
> and the project is now read-only.

![Shepherd](https://github.com/GhostManager/Shepherd/raw/master/Shepherd.jpg)

Shepherd is a Django application written in Python 3.7 and is designed to be used by a team of operators. It keeps track of domain names and each domain's current DNS settings, categorization, project history, and status. The tracked statuses include which domains are: ready to be used, burned/retired, or in use, and which team member checked out each of the active domains.

More information is available here: https://medium.com/@cmaddy/being-a-good-domain-shepherd-part-2-5e8597c3fe63

## Installation

Shepherd requires Redis server and Python 3.7. Install these before proceeding. The exact steps will depend on your operating system, but should be as simple as using an `apt install` or `brew install` command.

### Installing Libraries

All of Shepherd's Python/Django dependencies are documented in the Pipfile. It is easiest to setup and use a virtual environment using `pipenv`. This is the best option for managing the required libraries and to avoid Python installations getting mixed-up.

Do this:

1. Run: `pip3 install --user pipenv` or `python3 -m pip install --user pipenv`
2. Run: `git clone https://github.com/GhostManager/Shepherd.git`
3. Run: cd Shepherd && pipenv install
4. Start using Shepherd by running: pipenv shell

### Adjusting Settings.py

Once Django and the other Python libraries are installed, open Shepherd's settings.py file and direct your attention to the `SECRET_KEY` and `DEBUG` variables. You can set `DEBUG` to `True` if you want to test Shepherd or make some changes. It is a good idea to set this to `False` in production, even though Shepherd _should_ only be used as an internal resource.

The `SECRET_KEY` variable is set to `changeme`. Feel free to generate something and drop it in or use an environment variable. It's usually something like `cg#p$g+j9tax!#a3cup@1$8obt2_+&k3q+pmu)5%asj6yjpkag`.

### Additional Settings

#### API Configuration

Settings.py also stores API information for a few functions. One of Shepherd's core features is updating domain "health" data (more on that below). This uses web requests and part of it uses the VirusTotal API. If you do not have one, get a free API key from VirusTotal. Once you have your key add it to the `DOMAINCHECK_CONFIG` settings.

If you have a paid VirusTotal license and are not subject to the 4 requests per minute limit you can play with the `sleep_time` setting. A 20 second `sleep_time` is still recommended to avoid spewing web requests so fast that your IP address gets blocked with reCAPTCHAs, but you can try reducing it.

#### Slack Configuration

There is also a `SLACK_CONFIG` settings dictionary. If you have, or can get, a Slack Incoming Webhook you can configure that here to receive some messages when tasks are completed or domains are burned.

You can set a username and emoji for the bot. Emojis must be set using Slack syntax like `:sheep:`. The username can be anything you could use for a Slack username. The emoji will appear as the bot's avatar in channels.

The alert target is the message target. You can set this to a blank string, e.g. `''`, but it's mostly useful for targeting users, aliases, or @here/@channel. They must be written as `<!here>`, `<!channel>`, or `<@username>` for them to work as actual notification keywords.

Finally, set the target channel. This might be your `#general` or some other channel. This is the global value that will be used for all messages unless another value is supplied. Currently only the global value from settings.py is used but in the future there will be messages sent for specific projects and events. For example, when a domain is checked-out for use the user can specify a Slack channel to use for notifications and a future version of Shepherd, currently in the works, will use that channel to send project_related notifications to the provided the channel.

If you do not want to use Slack change `enable_slack` to `False`.

Other notification options are coming soon. Email and services such as Pushover are being considered.

### Database Setup

Next, the database tables must be migrated. This configures all of Shepherd's database models from the code in models.py to actual tables:

To setup the database run: `python3 manage.py migrate`

Assuming that completed successfully, you need to pre-populate a few of Shepherd's database models with some data. These are just some basic domain statuses and project types. You can add your own as desired later.

To initiate settings run: `python3 manage.py loaddata catalog/fixtures/initial_values.json`

### Start Django

A super user must now be created to access the admin panel and create new users and groups. This is the administrator of Shepherd, so set a strong password and document it in a password vault somewhere.

To create a superuser run: `python manage.py createsuperuser`

Finally, try starting the server and accessing the admin panel.

To start the server run: `python3 manage.py runserver`

Visit SERVER_IP:8000/admin to view the admin panel and login using the superuser.

### Creating New Users

Create your users using the admin panel. Filling out a complete profile is recommended.

In cases where Shepherd records a user action the usernames are used rather than first or last names, but Shepherd does display the user's full name in the corner if it is available. Also, usernames are weirdly case sensitive, so all lowercase is recommended to avoid confusion later.

Email addresses are not important at the present time, but this will change. Shepherd will use email addresses for password recovery, but the email server is not baked into Shepherd right now. Emails will just appear in the terminal and that is where the user or an administrator can get their password reset link.

In the future, email addresses will be displayed as a means of contacting the operator using a particular domain for domain and project questions. Email may also ne used to send notifications.

### Creating New Groups

Groups are a good way to organize user permissions. Shepherd will make a couple of functions available to a "Senior Operators" group, including editing a domain's information. To use this functionality create two groups named "Operators" and "Senior Operators" in the admin panel.

Only mark users as "Staff" if you want them to be able to access the Django admin panel. It is better to leave the admin panel alone for day-to-day work and it should not be required except to fix a problem or directly edit the database for some reason, so users do not require this access.

### Start Django Q and Redis

Once you are ready to actually use Shepherd start your Redis server. You also need to start Django Q's `qcluster` which will need to be done using another terminal window with manage.py, just like starting the server.

Run this: `python3 manage.py qcluster`

If Redis is running on a different server, you changed the port, or made some other modification, you will need to update the Redis configuration in settings.py. You could also switch to a different broker if you already have some other broker setup and would prefer to use it for Shepherd. Check Django Q's documentation to make the changes in settings.py to switch to Rabbit MQ, Amazon SQS, or whatever else you might be using.

### Schedule Tasks

Visit the Django Q database from the admin panel and check the Scheduled tasks. You may wish to create a scheduled task to automatically release domains at the end of a project. Shepherd has a task for this, `tasks.release_domains`, which you can schedule whenever you please, like every morning at 01:00.

## Notes on Health

Shepherd grades a domain's health as Healthy or Burned. Health is reported as an overall health grade and a separate grade for the domain's DNS. You will almost certainly see a `Healthy` domain with questionable DNS. This is not something to be worried about without some human investigation. The DNS is based on VirusTotal's passive DNS report and checking to see if the IP addresses have appeared in any threat reports. If you bought an expired domain it's not at all strange to learn it once pointed at a cloud IP address that was flagged for something naughty at some point.

Check to see if the IP addresses in question are yours. If they are not then you can probably ignore this. If the IP address was flagged very recently, like just before you bought the domain, then that may be a concern because the domain may be flagged for recent malicious activity.  There's a lot of "maybes" here because this is very much an imperfect grade.

In general, focus on the overall health status (based on categories) and just use the passive DNS information and flags to help with manual analysis of your domains.

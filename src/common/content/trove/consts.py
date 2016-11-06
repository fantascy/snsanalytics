from sets import ImmutableSet


API_KEY = "72ecd4e607a04185a5141d4fb662d5b5"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
MAX_INGESTION_LATENCY = 90 #minutes
USAGE_RIGHTS_FULL = 'full'
USAGE_RIGHTS_TBD = 'tbd'
USAGE_RIGHTS_SNIPPET = 'snippet'
USAGE_RIGHTS_NONE = 'none'
USAGE_RIGHTS_MAP = {USAGE_RIGHTS_FULL: 100, USAGE_RIGHTS_TBD: 75, USAGE_RIGHTS_SNIPPET: 50, USAGE_RIGHTS_NONE: 0}

UTM_SOURCE = "sns"
UTM_MEDIUM = "twitter"
UTM_CAMPAIGN_HOSTED = "hosted"
UTM_CAMPAIGN_UNHOSTED = "unhosted"

MENTION_NONE = 0
MENTION_PICKER = 1
MENTION_TROVE = 2
MENTION_BOTH = 3
MENTION_TYPES = tuple(range(4))
MENTION_TYPE_MAP = {
    MENTION_NONE: None,
    MENTION_PICKER: 'pmention',
    MENTION_TROVE: 'tmention',
    MENTION_BOTH: 'bmention',
    }

NEWS_FEED_PATTERN = "http://%s/troverss/%s/"

URL_STATE_UNINGESTED = 0
URL_STATE_HOSTED = 1
URL_STATE_UNHOSTED = 2
URL_STATES = tuple(range(3))

EXCLUDED_OWNER_IDS = set(['EC03537F68A00D63E040A80AF312609A'])

USER_AGENT = "SNS Analytics"


VISOR_NA            = 'N/A'
VISOR_UNINGESTED    = 'Uningested'
VISOR_FRAME_KILLER  = 'Frame Killer'
VISOR_PAGE_KILLER   = 'Page Killer'
VISOR_PHONE_KILLER  = 'Phone Killer'
VISOR_IPHONE_UNFRIENDLY  = 'iPhone Unfriendly'
VISOR_GREAT         = 'Great'
VISOR_GOOD          = 'Good'
VISOR_OK            = 'OK'
VISOR_BAD           = 'Bad'
VISOR_AWFUL         = 'Awful'
VISOR_STATES = ImmutableSet([VISOR_NA, VISOR_UNINGESTED, VISOR_FRAME_KILLER, VISOR_PAGE_KILLER, VISOR_PHONE_KILLER, VISOR_IPHONE_UNFRIENDLY, 
                    VISOR_GREAT, VISOR_GOOD, VISOR_OK, VISOR_BAD, VISOR_AWFUL])


SNS_BLACKLIST = [
'rantsports.com', 'mirror.co.uk', 'forbes.com', 'nypost.com', 'denverpost.com', 'stltoday.com', 'thestate.com', 'sacbee.com', 'fresnobee.com', 'idahostatesman.com', 'madison.com', 'globo.com', 'sanluisobispo.com', 'nytimes.com', 'insure.com', 'hark.com', 'anrdoezrs.net'
'el33tonline.com', 'mtlblog.com', 'lazygamer.net', 'potomaclocal.com',
]
EXTENDTED_SNS_BLACKLIST = [
'cbssports.com', 'cbslocal.com', 'chicagotribune.com', 'startribune.com', 'dispatch.com', 'post-gazette.com', 'youtube.com', 'bostonherald.com', 
'washingtontimes.com', 'hollywoodreporter.com', 'ndtv.com', 'triblive.com', 'bgr.com', 'macworld.com', 'globo.com', 'rantsports.com', 
'nypost.com', 'sacbee.com', 'fresnobee.com', 'idahostatesman.com', 'madison.com', 'freep.com', 'mirror.co.uk', 'fansided.com', 'sportingnews.com',
'newsok.com', 'philly.com', 'charlotteobserver.com', 'kentucky.com', 'buffalonews.com', 'seattlepi.com', 'sltrib.com', 'courier-journal.com',
'indystar.com', 'cincinnati.com', 'crossmap.com', 'globo.com', 'sportsnet.ca', 'hoopshabit.com', 'gamingbolt.com', 'sanluisobispo.com',
'uproxx.com', 'tomahawktake.com', 'nflspinzone.com', 'zap2it.com', 'gmenhq.com', 'theolympian.com', 'thebatt.com', 'recordnet.com',
'valleyofthesuns.com', 'ualrtrojans.com',
]
SNS_BLACKLIST.extend(EXTENDTED_SNS_BLACKLIST)

VISOR_UNFRIENDLY_LIST = [
'go.com', 'cbssports.com', 'yahoo.com', 'imgur.com', 'cbslocal.com', 'chicagotribune.com', 'startribune.com', 'dispatch.com', 'time.com', 'post-gazette.com', 'youtube.com', 'bostonherald.com', 'washingtontimes.com', 'hollywoodreporter.com', 'ndtv.com', 'triblive.com', 'bgr.com', 'macworld.com', 'fastcompany.com', 'si.com', 'forbes.com', 'globo.com', 'rantsports.com', 'mirror.co.uk', 'nypost.com', 'sacbee.com', 'fresnobee.com', 'idahostatesman.com', 'madison.com'
]

VISOR_PHONE_UNFRIENDLY_LIST = [
'huffingtonpost.com'
]

VISOR_IPHONE_UNFRIENDLY_LIST = [
'usatoday.com', 'cnn.com', 'nbcsports.com', 'theguardian.com', 'dallasnews.com', 'nydailynews.com', 'fansided.com', 'espnfc.com', 'newsok.com', 'chron.com', 'gamespot.com', 'detroitnews.com', 'justjared.com', 'mashable.com', 'broadwayworld.com', 'politico.com', 'wired.com', 'lasvegassun.com', 'billboard.com', 'hoopshabit.com', 'kpopstarz.com', 'dailystar.co.uk', 'uproxx.com', 'joystiq.com', 'tomahawktake.com', 'kvue.com', 'heavy.com', 'nflspinzone.com', 'sportsgrid.com', 'larrybrownsports.com', 'pcmag.com', 'proactiveinvestors.com', 'computerworld.com', 'euronews.com', '8newsnow.com', 'gmenhq.com', 'tubefilter.com', 'musketfire.com', 'latino.foxnews.com', 'espnfc.us', 'espnfc.co.uk', 'espnfc.com.au', 'harvardmagazine.com', 'caribjournal.com'
]

VISOR_FRIENDLY_LIST = [
'dailydot.com', 'fiusm.com', 'gizmag.com', 'foxnews.com', 'reuters.com', 'nj.com', 'latimes.com', 'mlive.com', 'cleveland.com', 'bbc.co.uk', 'oregonlive.com', 'nbcnews.com', 'ibtimes.com', 'hollywoodlife.com', 'celebdirtylaundry.com', 'mercurynews.com', 'telegraph.co.uk', 'nola.com', 'sfgate.com', 'cbc.ca', 'nba.com', 'eonline.com', 'cbsnews.com', 'independent.co.uk', 'newsobserver.com', 'kotaku.com', 'tmz.com', 'christiantoday.com', 'voanews.com', 'express.co.uk', 'nfl.com', 'usmagazine.com', 'ajc.com', 'mlb.com', 'mlssoccer.com', 'baltimoresun.com', 'azcentral.com', 'perezhilton.com', 'utsandiego.com', 'aljazeera.com', 'sun-sentinel.com', 'masslive.com', 'jsonline.com', 'tampabay.com', 'orlandosentinel.com', 'mtv.com', 'smh.com.au', 'thestar.com', 'rollingstone.com', 'csmonitor.com', 'metro.co.uk', 'cnet.com', 'irishtimes.com', 'bbc.com', 'newsday.com', 'goal.com', 'liverpoolecho.co.uk', 'toledoblade.com', 'npr.org', 'cinemablend.com', 'wkyt.com', 'wdrb.com', 'deadspin.com', 'wfaa.com', 'blastmagazine.com', 'techcrunch.com', 'pcgamer.com', 'theonion.com', 'rawstory.com', 'wrestlezone.com', 'geekwire.com', 'stereogum.com', 'rappler.com', 'peoplestylewatch.com', 'investors.com', 'space.com', 'sci-news.com', 'marieclaire.co.uk', 'dailymail.co.uk', 'inquisitr.com', 'freep.com', 'people.com', 'sportingnews.com', 'philly.com', 'christianpost.com', 'courier-journal.com', 'marketwatch.com', 'indystar.com', 'cincinnati.com', 'zap2it.com', 'theolympian.com', 'charlotteobserver.com', 'sltrib.com'
]

VISOR_UNFRIENDLY_LIST_BY_TROVE = [
    'allafrica.com',
    'appadvice.com',
    'appshopper.com',
    'arcticjournal.com',
    'blog.longreads.com',
    'blog.us.playstation.com',
    'blogs.adobe.com',
    'bloomberg.com',
    'businessweek.com',
    'cbslocal.com',
    'cen.acs.org',
    'chinafile.com',
    'community.plus.net',
    'coolhunting.com'
    'dailyherald.com',
    'deathvalleyvoice.com',
    'denverinfill.com',
    'designnews.com',
    'desiringgod.org',
    'dlisted.com',
    'domain-b.com',
    'earthobservatory.nasa.gov',
    'eco-business.com',
    'edsurge.com',
    'eetimes.com',
    'espn.go.com',
    'examiner.com',
    'facebook.com',
    'forbes.com'
    'google.com',
    'm.huffpost.com',
    'ibtimes.comonegreenplanet.org',
    'illawarramercury.com.au',
    'isc.sans.edu',
    'isource.com',
    'jamaica-gleaner.com',
    'japantimes.co.jp',
    'kickstarter.com',
    'linkedin.com',
    'livemint.com',
    'macrumors.com',
    'medium.com',
    'metro.us',
    'moneymanagement.com.au',
    'msn.com',
    'ndtv.com',
    'nytimes.com',
    'oliverelliott.org'
    'patch.com',
    'pepysdiary.com',
    'phandroid.com',
    'pocket-lint.com',
    'post-gazette.com',
    'programmableweb.com',
    'prweb.com',
    'reviewed.com',
    'rotoworld.com',
    'scpr.org',
    'shortnews.com',
    'si.com',
    'sobadsogood.com',
    'softpedia.com',
    'soundcloud.com',
    'sourceforge.net',
    'spendmatters.com',
    'startribune.com',
    'stockhouse.com',
    'sunlightfoundation.com',
    'theblaze.com',
    'theconversation.com',
    'thedodo.com',
    'theherald.com.au',
    'thehimalayantimes.com',
    'thehollywoodgossip.com',
    'time.com',
    'universityworldnews.com',
    'villagesoup.com',
    'vimeo.com',
    'vox.com',
    'whatstrending.com',
    'wildsnow.com',
    'worldbank.org',
    'yahoo.com',
    'youtube.com',
    '9gag.com',
]

_temp_list = []
_temp_list.extend(SNS_BLACKLIST)
_temp_list.extend(VISOR_UNFRIENDLY_LIST)
_temp_list.extend(VISOR_UNFRIENDLY_LIST_BY_TROVE)
VISOR_UNFRIENDLY_BLACKSET = ImmutableSet(_temp_list)
_temp_list.extend(VISOR_PHONE_UNFRIENDLY_LIST)
VISOR_PHONE_UNFRIENDLY_BLACKSET = ImmutableSet(_temp_list)
_temp_list.extend(VISOR_IPHONE_UNFRIENDLY_LIST)
VISOR_IPHONE_UNFRIENDLY_BLACKSET = ImmutableSet(_temp_list)
_temp_list = []
_temp_list.extend(VISOR_FRIENDLY_LIST)
VISOR_FRIENDLY_WHITESET = ImmutableSet(_temp_list)
_temp_list.extend(VISOR_PHONE_UNFRIENDLY_LIST)
_temp_list.extend(VISOR_IPHONE_UNFRIENDLY_LIST)
VISOR_POSSIBLY_FRIENDLY_WHITESET = ImmutableSet(_temp_list)
del _temp_list
del VISOR_UNFRIENDLY_LIST
del VISOR_UNFRIENDLY_LIST_BY_TROVE
del VISOR_PHONE_UNFRIENDLY_LIST
del VISOR_IPHONE_UNFRIENDLY_LIST


_HOSTED_URL_WHITELIST = [
    "http://hosted.ap.org",
    "http://www.slate.com",
    "http://www.salon.com",
    "http://msn.foxsports.com",
    "http://www.reuters.com",
    "http://washingtonpost.com",
    "http://www.fool.com",
    "http://www.philstar.com",
    "http://www.dailycal.org",
    "http://www.menshealth.com",
    "http://www.beliefnet.com",
    "http://www.theatlantic.com",
    "http://www.pitchfork.com",
    "http://www.foreignpolicy.com",
    "http://gigaom.com",
    "http://www.sbnation.com",
    "http://www.halosheaven.com",
    "http://www.athleticsnation.com",
    "http://www.lookoutlanding.com",
    "http://www.lonestarball.com",
    "http://www.southsidesox.com",
    "http://www.letsgotribe.com",
    "http://www.bluebirdbanter.com",
    "http://www.draysbay.com",
    "http://www.overthemonster.com",
    "http://www.camdenchat.com",
    "http://www.twinkietown.com",
    "http://www.royalsreview.com",
    "http://www.blessyouboys.com",
    "http://www.beyondtheboxscore.com",
    "http://www.minorleagueball.com",
    "http://www.federalbaseball.com",
    "http://www.thegoodphight.com",
    "http://www.amazinavenue.com",
    "http://www.fishstripes.com",
    "http://www.talkingchop.com",
    "http://www.vivaelbirdos.com",
    "http://www.bucsdugout.com",
    "http://www.brewcrewball.com",
    "http://www.crawfishboxes.com",
    "http://www.redreporter.com",
    "http://www.bleedcubbieblue.com",
    "http://www.mccoveychronicles.com",
    "http://www.gaslampball.com",
    "http://www.truebluela.com",
    "http://www.purplerow.com",
    "http://www.azsnakepit.com",
    "http://www.bulletsforever.com",
    "http://www.poundingtherock.com",
    "http://www.sactownroyalty.com",
    "http://www.blazersedge.com",
    "http://www.brightsideofthesun.com",
    "http://www.postingandtoasting.com",
    "http://www.brewhoop.com",
    "http://www.clipsnation.com",
    "http://www.indycornrows.com",
    "http://www.goldenstateofmind.com",
    "http://www.mavsmoneyball.com",
    "http://www.blogabull.com",
    "http://www.tomahawknation.com",
    "http://www.carolinamarch.com",
    "http://www.cardchronicle.com",
    "http://www.BlockU.com",
    "http://www.maizenbrew.com",
    "http://www.blackheartgoldpants.com",
    "http://www.conquestchronicles.com",
    "http://www.buildingthedam.com",
    "http://www.bruinsnation.com",
    "http://www.addictedtoquack.com",
    "http://www.rollbamaroll.com",
    "http://www.rockytoptalk.com",
    "http://www.garnetandblackattack.com",
    "http://www.dawgsports.com",
    "http://www.andthevalleyshook.com",
    "http://www.alligatorarmy.com",
    "http://www.aseaofblue.com",
    "http://www.rockmnation.com",
    "http://www.rockchalktalk.com",
    "http://www.doubletnation.com",
    "http://www.crimsonandcreammachine.com",
    "http://www.burntorangenation.com",
    "http://www.bringonthecats.com",
    "http://www.windycitygridiron.com",
    "http://www.prideofdetroit.com",
    "http://www.acmepackingcompany.com",
    "http://www.dailynorseman.com",
    "http://www.baltimorebeatdown.com",
    "http://www.cincyjungle.com",
    "http://www.dawgsbynature.com",
    "http://www.behindthesteelcurtain.com",
    "http://www.mockingthedraft.com",
    "http://www.thefalcoholic.com",
    "http://www.canalstreetchronicles.com",
    "http://www.battleredblog.com",
    "http://www.stampedeblue.com",
    "http://www.bigcatcountry.com",
    "http://www.musiccitymiracles.com",
    "http://www.bloggingtheboys.com",
    "http://www.bigblueview.com",
    "http://www.bleedinggreennation.com",
    "http://www.hogshaven.com",
    "http://www.buffalorumblings.com",
    "http://www.thephinsider.com",
    "http://www.patspulpit.com",
    "http://www.revengeofthebirds.com",
    "http://www.ninersnation.com",
    "http://www.fieldgulls.com",
    "http://www.turfshowtimes.com",
    "http://www.milehighreport.com",
    "http://www.arrowheadpride.com",
    "http://www.silverandblackpride.com",
    "http://www.faketeams.com",
    "http://www.diebytheblade.com",
    "http://www.secondcityhockey.com",
    "http://www.milehighhockey.com",
    "http://www.wingingitinmotown.com",
    "http://www.hockeywilderness.com",
    "http://www.pensburgh.com",
    "http://www.fearthefin.com",
    "http://www.pensionplanpuppets.com",
    "http://www.badlefthook.com",
    "http://www.bloodyelbow.com",
    "http://www.fitsugar.com",
    "http://www.ridiculousupside.com",
    "http://www.thedailybeast.com",
    "http://bleacherreport.com",
    "http://geeksugar.com",
    "http://buzzsugar.com",
    "http://www.savvysugar.com",
    "http://www.detroitbadboys.com",
    "http://thedreamshake.blogspot.com",
    "http://www.catscratchreader.com",
    "http://www.globalpost.com",
    "http://www.dnaindia.com",
    "http://www.businessinsider.com",
    "http://www.womenshealthmag.com",
    "http://www.deadline.com",
    "http://www.heraldnet.com",
    "http://www.alaskadispatch.com",
    "http://www.jacketscannon.com",
    "http://www.obnug.com",
    "http://thenextweb.com",
    "http://www.hammerandrails.com",
    "http://www.avclub.com/",
    "http://www.theroot.com",
    "http://www.expressnightout.com",
    "http://www.fairfaxtimes.com",
    "http://www.ksat.com",
    "http://www.cottagersconfidential.com",
    "http://www.mmamania.com",
    "http://www.cagesideseats.com",
    "http://www.clickondetroit.com",
    "http://www.click2houston.com",
    "http://www.local10.com",
    "http://www.clickorlando.com",
    "http://www.news4jax.com",
    "http://www.thestar.com",
    "http://www.orlandopinstripedpost.com",
    "http://www.libertyballers.com",
    "http://www.raptorshq.com",
    "http://www.slcdunk.com",
    "http://www.big12hoops.com",
    "http://www.houseofsparky.com",
    "http://www.hustlebelt.com",
    "http://www.ralphiereport.com",
    "http://www.azdesertswarm.com",
    "http://www.ubbullrun.com",
    "http://www.californiagoldenblogs.com",
    "http://www.redandblackattack.com",
    "http://www.ruleoftree.com",
    "http://www.cornnation.com",
    "http://www.capitalnewyork.com",
    "http://www.thehoya.com",
    "http://www.browndailyherald.com",
    "http://thedartmouth.com",
    "http://www.thecrimson.com",
    "http://www.yaledailynews.com",
    "http://www.mndaily.com",
    "http://badgerherald.com",
    "http://www.uwdawgpound.com",
    "http://www.vanquishthefoe.com",
    "http://www.mwcconnection.com",
    "http://www.cowboysrideforfree.com",
    "http://www.cougcenter.com",
    "http://www.cowboyaltitude.com",
    "http://www.offtackleempire.com",
    "http://www.midmajormadness.com",
    "http://www.collegecrosse.com",
    "http://www.teamspeedkills.com",
    "http://ajr.org",
    "http://www.crimsonquarry.com",
    "http://www.downthedrive.com",
    "http://www.arkansasexpats.com",
    "http://www.theuconnblog.com",
    "http://www.theonlycolors.com",
    "http://www.casualhoya.com",
    "http://www.thedailygopher.com",
    "http://www.sippinonpurple.com",
    "http://www.cardiachill.com",
    "http://www.redcuprebellion.com",
    "http://www.onthebanks.com",
    "http://www.forwhomthecowbelltolls.com",
    "http://www.southorangejuice.com",
    "http://www.buckys5thquarter.com",
    "http://www.voodoofive.com",
    "http://www.nunesmagician.com",
    "http://www.anchorofgold.com",
    "http://www.smokingmusket.com",
    "http://www.bcinterruption.com",
    "http://www.shakinthesouthland.com",
    "http://www.fromtherumbleseat.com",
    "http://www.testudotimes.com",
    "http://www.stateoftheu.com/",
    "http://www.backingthepack.com",
    "http://www.streakingthelawn.com",
    "http://www.gobblercountry.com",
    "http://www.bloggersodear.com",
    "http://www.bloggingthebracket.com",
    "http://www.searchingforbillyedelin.com",
    "http://www.minerrush.com",
    "http://www.inlouwetrust.com",
    "http://www.matchsticksandgasoline.com",
    "http://www.lighthousehockey.com",
    "http://www.blueshirtbanter.com",
    "http://www.coppernblue.com",
    "http://www.broadstreethockey.com",
    "http://www.nucksmisconduct.com",
    "http://www.stanleycupofchowder.com",
    "http://www.habseyesontheprize.com",
    "http://www.silversevensens.com",
    "http://www.ontheforecheck.com",
    "http://www.stlouisgametime.com",
    "http://www.battleofcali.com",
    "http://www.canescountry.com",
    "http://www.anaheimcalling.com",
    "http://www.litterboxcats.com",
    "http://www.defendingbigd.com",
    "http://www.rawcharge.com",
    "http://www.jewelsfromthecrown.com",
    "http://www.japersrink.com",
    "http://www.fiveforhowling.com",
    "http://www.fantasyhockeyscouts.com",
    "http://www.puckworlds.com",
    "http://www.westerncollegehockeyblog.com",
    "http://www.blackandredunited.com",
    "http://www.anfieldasylum.com",
    "http://www.bigdsoccer.com",
    "http://www.bitterandblue.com",
    "http://www.dynamotheory.com",
    "http://www.barcablaugranes.com",
    "http://www.thebusbybabe.com",
    "http://www.thedailywiz.com",
    "http://www.cartilagefreecaptain.com",
    "http://www.onceametro.com",
    "http://www.theshortfuse.com",
    "http://www.brotherlygame.com",
    "http://www.7500toholte.com",
    "http://www.eightysixforever.com",
    "http://www.stumptownfooty.com",
    "http://www.weaintgotnohistory.com",
    "http://www.hottimeinoldtown.com",
    "http://www.rslsoapbox.com",
    "http://www.royalbluemersey.com",
    "http://www.burgundywave.com",
    "http://www.sounderatheart.com",
    "http://www.stiffjab.net",
    "http://www.texastribune.org",
    "http://www.lilsugar.com",
    "http://www.tressugar.com",
    "http://www.bellasugar.com",
    "http://www.wetpaint.com",
    "http://www.denverstiffs.com",
    "http://www.mlbdailydish.com",
    "http://www.bucsnation.com",
    "http://www.celticsblog.com",
    "http://www.hothothoops.com",
    "http://www.theverge.com",
    "http://www.netsdaily.com",
    "http://www.rodale.com",
    "http://organicgardening.com",
    "http://www.wbur.org",
    "http://www.gazette.net",
    "http://stream.aljazeera.com",
    "http://www.breakingnews.ie",
    "http://www.wapolabs.com",
    "http://blog.cityeats.com",
    "http://pandodaily.com",
    "http://www.cricketcountry.com",
    "http://www.bollywoodlife.com",
    "http://www.scpr.org",
    "http://www.ivillage.com",
    "http://www.smithsonianmag.com",
    "http://travel.india.com",
    "http://www.leedsstudent.org",
    "http://www.mmafighting.com",
    "http://worldcrunch.com",
    "http://www.arcticicehockey.com",
    "http://techcocktail.com",
    "http://www.royalcaribbean.com",
    "http://en.vogue.fr",
    "http://popdust.com",
    "http://sfpublicpress.org",
    "http://www.nowthisnews.com",
    "http://sportsmedia101.com",
    "http://www.collegeandmagnolia.com",
    "http://www.ourdailybears.com",
    "http://www.bigeastcoastbias.com",
    "http://www.dukebasketballreport.com",
    "http://www.widerightnattylite.com",
    "http://www.anonymouseagle.com",
    "http://www.onefootdown.com",
    "http://www.landgrantholyland.com",
    "http://www.rumbleinthegarden.com",
    "http://www.frogsowar.com",
    "http://www.goodbullhunting.com",
    "http://www.barkingcarnival.com",
    "http://www.vuhoops.com",
    "http://www.pacifictakes.com",
    "http://www.pinstripedbible.com",
    "http://www.canishoopus.com",
    "http://www.silverscreenandroll.com",
    "http://www.rufusonfire.com",
    "http://www.peachtreehoops.com",
    "http://www.welcometoloudcity.com",
    "http://www.fearthesword.com",
    "http://www.swishappeal.com",
    "http://www.thebirdwrites.com",
    "http://www.grizzlybearblues.com",
    "http://www.ganggreennation.com",
    "http://www.boltsfromtheblue.com",
    "http://www.quakerattleandgoal.com",
    "http://www.lagconfidential.com",
    "http://www.wakingthered.com",
    "http://www.thegoatparade.com",
    "http://www.thebentmusket.com",
    "http://www.villarrealusa.com",
    "http://www.managingmadrid.com",
    "http://www.cominghomenewcastle.com",
    "http://www.mountroyalsoccer.com",
    "http://www.lionofviennasuite.com",
    "http://www.pieeatersfootie.com",
    "http://www.throughitalltogether.com",
    "http://www.rokerreport.com",
    "http://www.thetilehurstend.com",
    "http://www.bavarianfootballworks.com",
    "http://inter.theoffside.com",
    "http://acmilan.theoffside.com",
    "http://www.chiesaditotti.com",
    "http://www.blackwhitereadallover.com",
    "http://www.fmfstateofmind.com",
    "http://www.nevermanagealone.com",
    "http://www.stridenation.com",
    "http://losangeles.sbnation.com",
    "http://dallas.sbnation.com",
    "http://pittsburgh.sbnation.com",
    "http://seattle.sbnation.com",
    "http://stlouis.sbnation.com",
    "http://tampabay.sbnation.com",
    "http://kansascity.sbnation.com",
    "http://minnesota.sbnation.com",
    "http://philly.sbnation.com",
    "http://arizona.sbnation.com",
    "http://denver.sbnation.com",
    "http://detroit.sbnation.com",
    "http://atlanta.sbnation.com",
    "http://dc.sbnation.com",
    "http://houston.sbnation.com",
    "http://bayarea.sbnation.com",
    "http://chicago.sbnation.com",
    "http://newyork.sbnation.com",
    "http://boston.sbnation.com",
    "http://cleveland.sbnation.com",
    "http://www.sbnation.com",
    "http://liverpool.theoffside.com",
    "http://www.outsports.com",
    "http://cnsmaryland.org",
    "http://resoundmagazine.com",
    "http://mode.github.io",
    "http://live.wsj.com",
    "http://www.tytnetwork.com",
    "http://1776dc.com",
    "http://blog.trove.com",
    "http://www.tytnetwork.com",
    "http://www.hardwoodinsiders.com",
    "http://greatist.com",
                  ]
 
 
from common.utils import url as url_util
def _get_hosted_domains():
    hosted_domains = set([])
    for url in _HOSTED_URL_WHITELIST:
        domain = url_util.root_domain(url)
        if not domain in hosted_domains:
            hosted_domains.add(domain)
    return hosted_domains
HOSTED_WHITESET = _get_hosted_domains()


URL_CORRECTNESS_VALIDATION_WHITESET = set(["variety.com", ])


NON_REDIRECT_WHITESET = set(["reuters.com", ])


TOPIC_KEY_BLACKSET = set(['jainism', ])

    
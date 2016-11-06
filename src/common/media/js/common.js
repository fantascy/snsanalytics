/* These global variables need to be set by most top level pages. */ 
var APP = null;
var APP_PATH = null;
var MEDIA_PATH = "/";
var SHORT_URL_LENGTH = null;

function commonImagePath(name){
	return MEDIA_PATH + "common/images/" + name;
}

function appImagePath(name){
	return MEDIA_PATH + APP + "/images/" + name;
}

function hide(selector) {
	$(selector).addClass('ui-helper-hidden');
}

function show(selector) {
	$(selector).removeClass('ui-helper-hidden');
}



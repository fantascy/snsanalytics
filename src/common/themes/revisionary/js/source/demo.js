
/* 
/*	The following code is being included only to make special features work in the online demo. 
/*	This includes things like the skin changer and other not theme related items. You do not 
/*	need to have this file in your production website.
*/

//
// Load after the page is completed
// --------------------------------

jQuery(document).ready(function($) {
							
	// force starting slide on demo home
	if ($('#Slides').length > 0) {
		$('#Slides').cycle(7);
	}

	// prevent demo links using placeholder URL (href="#") from jumping to top
	$("a[href='#']").click( function(){
		return false;
	});	

	
});

//
// Cookies for remembering skins
// -----------------------------

/** Cookie plugin * Copyright (c) 2006 Klaus Hartl (stilbuero.de). Dual licensed under the MIT and GPL licenses: http://www.opensource.org/licenses/mit-license.php, http://www.gnu.org/licenses/gpl.html */
jQuery.cookie=function(b,j,m){if(typeof j!="undefined"){m=m||{};if(j===null){j="";m.expires=-1}var e="";if(m.expires&&(typeof m.expires=="number"||m.expires.toUTCString)){var f;if(typeof m.expires=="number"){f=new Date();f.setTime(f.getTime()+(m.expires*24*60*60*1000))}else{f=m.expires}e="; expires="+f.toUTCString()}var l=m.path?"; path="+(m.path):"";var g=m.domain?"; domain="+(m.domain):"";var a=m.secure?"; secure":"";document.cookie=[b,"=",encodeURIComponent(j),e,l,g,a].join("")}else{var d=null;if(document.cookie&&document.cookie!=""){var k=document.cookie.split(";");for(var h=0;h<k.length;h++){var c=jQuery.trim(k[h]);if(c.substring(0,b.length+1)==(b+"=")){d=decodeURIComponent(c.substring(b.length+1));break}}}return d}};

//
// Skin switch function
// ---------------------------
function switchSkin(skin) {
	jQuery.cookie("skin", skin);
	document.location.reload(true);
	return false;
}

//
// Include skin style sheet 
// (only necessary if using dynamic skin switching)
// ----------------------------------------------------
	// some default variables
	var skin = jQuery.cookie("skin") || "1";
	var skinCSS = document.getElementById('SkinCSS');
	var last = skinCSS.href.lastIndexOf('/') + 1;
	var cssPath = skinCSS.href.substring(0,last);
	var fileName = "skin-"; //"style-skin-";
	
	// set the skin CSS file
	skinCSS.href = cssPath + fileName + skin + ".css";
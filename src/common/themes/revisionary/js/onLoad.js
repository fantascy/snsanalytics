/*
/*	Dynamic design functions and onLoad events
/*	----------------------------------------------------------------------
/* 	Creates added dynamic functions and initializes loading.
*/


// ======================================================================
//
//	On document ready functions
//
// ======================================================================

jQuery(document).ready(function($) {
	

	if (typeof(jQuery.fancybox) == 'function') {
		
		// initialize modal (fancybox)
		// -------------------------------------------------------------------
		
		// Quickly setup some special references
		// fancybox doesn't like #name references at the end of links so we find
		// them and modify the link to use a class and remove the #name.
		$('a[href$="#popup"]').addClass('iframe').each( function() {
			$(this).attr('href', this.href.replace('#popup',''));
		});
		
		// setup fancybox for YouTube
		$("a.zoom[href*='http://www.youtube.com/watch?']").each( function() {
			$(this).addClass('fancyYouTube').removeClass('zoom');
		});
	
		// setup fancybox for Vimeo
		$("a.zoom[href*='http://www.vimeo.com/']").each( function() {
			$(this).addClass('fancyVimeo').removeClass('zoom');
		});
		
	
		var overlayColor = '#2c2c2c';
		
		function fancyTitleFormat(title) {
			var customTitle = '<div id="Fancybox-CustomTitle"><span id="Fancybox-CustomClose"><a href="javascript:;" onclick="jQuery.fancybox.close();">Close</a></span>' + title + '</div>';
			return (title.length > 0) ? customTitle : null;
		}
	
		function fancyAfterLoad() {
			
			// show/hide close button
			if (jQuery('#Fancybox-CustomTitle').length <= 0) {
				jQuery('#fancybox-close').css('display','block');	
			}
			
			// extra button styling
			jQuery('#fancybox-left-ico, #fancybox-right-ico').css({
				'-moz-border-radius': '3px',
				'-webkit-border-radius': '3px',
				'border-radius': '3px'
			});

		}
		
		// fancybox - default
		$('a.zoom').fancybox({
			'padding': 0,
			'titlePosition': 'inside',
			'titleFormat': fancyTitleFormat,
			'showCloseButton': false,
			'href': this.href,
			'transitionIn': 'elastic',
			'transitionOut': 'elastic',
			'overlayOpacity': 0.2,
			'onComplete': fancyAfterLoad
		});
		
		// fancybox - YouTube
		$('a.fancyYouTube').click(function() {
			jQuery.fancybox({
				'padding': 0,
				'titlePosition': 'inside',
				'titleFormat': fancyTitleFormat,
				'showCloseButton': false,
				'transitionIn': 'elastic',
				'transitionOut': 'elastic',
				'overlayOpacity': 0.2,
				'overlayColor': overlayColor, 
				'title': this.title,
				'href': this.href.replace(new RegExp("watch\\?v=", "i"), 'v/'),
				'type': 'swf',
				'swf': {
					'wmode': 'transparent',
					'allowfullscreen'	: 'true'}, // <-- flashvars
				'onComplete': fancyAfterLoad
			});
			return false;
		});
	
		// fancybox - Vimeo	
		$("a.fancyVimeo").click(function() {
			jQuery.fancybox({
				'padding': 0,
				'titlePosition': 'inside',
				'titleFormat': fancyTitleFormat,
				'showCloseButton': false,
				'transitionIn': 'elastic',
				'transitionOut': 'elastic',
				'overlayOpacity': 0.2,
				'overlayColor': overlayColor, 
				'title': this.title,
				'href': this.href.replace(new RegExp("([0-9])","i"),'moogaloop.swf?clip_id=$1'),
				'type': 'swf',
				'onComplete': fancyAfterLoad
			});
			return false;
		});
		
	} // end (typeof(jQuery.fancybox) == 'function')

	
	// Text and password input styling
	// -------------------------------------------------------------------
	
	// This should be in the CSS file but IE 6 will ignore it.
	// If you have an input you don't want styles, add the class "noStyle"

	$("input[type='text']:not(.noStyle), input[type='password']:not(.noStyle)").each(function(){
		$(this).addClass('textInput');
	});
	// Focus and blur style changing
	$('.textInput').blur( function() {
		$(this).removeClass('inputFocus');
	}).focus( function() {
		$(this).addClass('inputFocus');
	});
	
	
	// FAQ's functionality
	// -------------------------------------------------------------------
	if ($('.faqs li').length > 0 ) {
		var faqs = $('.faqs li');
		faqs.each( function() {
			var q = $(this);
			q.children('.question').click( function() {
				q.children('div').slideToggle('fast', function() {
					// Animation complete...
				});
			});
		});
	}


	// input lable replacement
	// -------------------------------------------------------------------
	$("label.overlabel").overlabel();
	
	// apply custom button styles
	// -------------------------------------------------------------------
	buttonStyles(jQuery);

});



// ======================================================================
//
//	Design functions
//
// ======================================================================


// button styling function
// -------------------------------------------------------------------

function buttonStyles($) {
	// Button styles
	
	// This will style buttons to match the theme. If you don't want a button
	// styled, give it the class "noStyle" and it will be skipped.
	$("button:not(:has(span),.noStyle), input[type='submit']:not(.noStyle), input[type='button']:not(.noStyle)").each(function(){
		var	b = $(this),
			tt = b.html() || b.val();
		
		// convert submit inputs into buttons
		if (!b.html()) {
			b = ($(this).attr('type') == 'submit') ? $('<button type="submit">') : $('<button>');
			b.insertAfter(this).addClass(this.className).attr('id',this.id);
			$(this).remove();	// remove input
		}
		b.text('').addClass('btn').append($('<span>').html(tt));	// rebuilds the button
	});
	
	// Get all styled buttons
	var styledButtons = $('.btn');
	
	// Fix minor problem with Mozilla and WebKit rendering (can also be done adding this to CSS, 
	// button::-moz-focus-inner {border: none;}
	// @media screen and (-webkit-min-device-pixel-ratio:0) { button span {margin-top: -1px;} }
	if (jQuery.browser.mozilla || jQuery.browser.webkit) {
		styledButtons.children("span").css("margin-top", "-1px");
	}
	
	// Button hover class (IE 6 needs this)
	styledButtons.hover(
		function(){ $(this).addClass('submitBtnHover'); },		// mouseover
		function(){ $(this).removeClass('submitBtnHover'); }	// mouseout
	);
}



// Apply font replacement (cufon)
// -------------------------------------------------------------------
Cufon.replace('h1, h2, h3, h4, h5, h6, .postDate')
	('#Slides li h3', { textShadow: '1px 1px 2px rgba( 0, 0, 0, .5 )'});

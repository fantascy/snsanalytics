/**
 * Copyright (c) 2010 Andy Wilkerson (Parallelus)
 *
 * Version: 1.0
 * Requires: jQuery v1.4.2 or later
 *
 */

jQuery(document).ready(function($) {
	
	var firstCycle = true; // var to track start of cycle
	
	if ($('#Slides li').length > 0) {
		
		if (jQuery(this).find('.fullWidth').length <= 0) {
		
			// we only use the grid when not showing the full width slider
			$('#Slides').children('li').each( function(index, value) {
			
				// variables
				var href = jQuery(this).find("a").attr("href") || '#',
					src = jQuery(this).find("img.slideThumb").attr("src") || jQuery(this).find("img").attr("src"),
					theClass = 'slideItem';
					
				// check for multi-box slides
				if ($(this).hasClass('double')) {
					theClass += ' slideDouble';
				}
				
				// test if the title needs a badkground overlay
				$(this).find('.showBg').after(
					$('<div class="titleBg"></div>').css({
						'opacity': .6,
						'height': $(this).find('.showBg').height() + 15 + 'px'
					})
				);
				
				// add grid elements to page
				thumbCtnr = jQuery('<div class="'+theClass+'" id="SlidesIndex-'+index+'"></div>')
					.css('cursor','pointer')
					// adding a click command because IE sucks
					.click( function() { 
						document.location.href = href; 
						return false;
					});				
				thumbLink = jQuery('<a href="'+href+'" class="slideImg"></a>')
				jQuery('#Featured').append(thumbCtnr.append(thumbLink));
				
				// add grid image
				var thumbImg = new Image();
				jQuery(thumbImg).load(function () {
					if (jQuery.browser.msie && parseInt(jQuery.browser.version, 10) <= 7) { 
						// gettin the size for positioning won't work for IE so we skip it
					} else {
						// all other browsers, let's center the position of the image thumbnail
						left = Math.floor( ($(this).width() - $(this).parent().outerWidth()) / 2);
						$(this).css({
							'left': - left + 'px'
						});
					}
				}).attr('src', src).addClass('gridThumb').prependTo(thumbCtnr);
				
				thumbCtnr.hoverIntent(
					function() {
						jQuery('#Slides').cycle(index);		// switch the main slide to the hovered thumbnail
						jQuery('#Slides').cycle('pause');	// pause while hovering
					}, 
					function() {
						jQuery('#Slides').cycle('resume');	// resume after mouseout
					}
				);
				
				// add the slide info (text) container
				if ( index == 1 || jQuery('#Slides li').length == 1) {
					slideTextContainer(); // insert text container
				}
			});
		
		} else { // IF NOT showing grid thumbnails
		
		
			// Prepare slides needing title BG Overlay
			$('#Slides > li').children('.showBg').each( function(index, value) {
				
				// add bg overlay
				$(this).after(
					$('<div class="titleBg"></div>').css({
						'opacity': .6,
						'height': $(this).height() + 15 + 'px'
					})
				);
			});
			
			// show the slide text info box
			slideTextContainer('fullWidth');
			
		} // IF NOT jQuery(this).find('.fullWidth').length > 0
		
		// activate cycle plugin
		$('#Slides').cycle({ 
			fx: 'fade',
			random: true,
			pause: true, // pause on hover
			speed: 600,
			timeout: 4000, 
			randomizeEffects: false, 
			easing: 'easeOutCubic',
			before: function(curr, next, opts) {
				if (!firstCycle) {
					// if not first cycle, normal switching
					jQuery('#SlidesIndex-' + opts.currSlide).removeClass('activeSlide');
					jQuery('#SlidesIndex-' + opts.nextSlide).addClass('activeSlide');
					var desc = jQuery(next).find('.slideDesc').html();
					var href = jQuery(next).find("a").attr("href") || '#'; // get hyperlink to full article
				} else {
					// first cycle, mark first slide active
					jQuery('#SlidesIndex-' + opts.currSlide).addClass('activeSlide');
					var desc = jQuery(curr).find('.slideDesc').html();
					var href = jQuery(curr).find("a").attr("href") || '#'; // get hyperlink to full article
				}
				// add hyperlink to button
				if (href == '#') {
					jQuery('#SlideInfo-Button').css('display','none');
				} else {
					jQuery('#SlideInfo-Button').css('display','block').click( function(){ document.location.href = href; });
				}
				// add description text to the slide info
				jQuery('#SlideInfo-Text').html(desc);
			},
			after: function(curr, next, opts) { 
				firstCycle = false;  // set to false as transitioning to second slide.
				$(next).find('.titleBg').css('height',$(next).find('.showBg').height() + 15 + 'px');  // check height of title bg overlay
			}
		});
		
		// add clear element at end of featured area
		jQuery('#Featured').append('<div class="clear"></div>');
		
	}
	
});


// function to create the slide description container
function slideTextContainer(c) {
	jQuery('#Featured').append(
		slideInfo = jQuery('<div id="SlideInfo" class="'+ c +'"></div>').append(
			slideText = jQuery('<div id="SlideInfo-Text"></div>')).append(
			slideButton = jQuery('<div id="SlideInfo-Button"><div class="slideInfo-ButtonBg">Continue reading...</div><span class="slideInfo-ButtonText">Continue reading...</span></div>'))
	);
	// a little button styling... and hover effects
	jQuery('.slideInfo-ButtonBg').css('opacity',0.13)
	slideButton.hover(
		function() {
			jQuery('.slideInfo-ButtonBg').css('opacity',0.28);	// mouse over
		}, 
		function() {
			jQuery('.slideInfo-ButtonBg').css('opacity',0.13);	// mouse out
		}
	);
	// some basic slide info hover actions
	slideInfo.hoverIntent(
		function() {
			jQuery('#Slides').cycle('pause');	// pause while hovering
		}, 
		function() {
			jQuery('#Slides').cycle('resume');	// resume after mouseout
		}
	);
}

